from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from database import get_db
from models import Patient, Doctor, Appointment, Billing, EHR, Staff, Role, Inventory, LabTest, Prescription, Consent, DoctorAvailability, Receipt, EHRVersion, Service
import schemas
from utils import create_payment_intent, require_roles, get_current_user, get_current_patient, get_password_hash, verify_password, create_access_token
from hms_logging import log_action

from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, extract
from fastapi import Body
from blockchain import blockchain
from database import get_db
from sqlalchemy.orm import Session
from models import Billing
from datetime import datetime, timedelta
from utils import create_access_token
import json

try:
    import requests
except Exception:
    requests = None

router = APIRouter()

# --- Prescriptions ---
@router.post("/prescriptions/", response_model=schemas.Prescription)
def create_prescription(p: schemas.PrescriptionCreate, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Doctor"))):
    new = Prescription(**p.dict())
    db.add(new)
    db.commit()
    db.refresh(new)
    log_action(user.id, f"Created prescription {new.id} for patient {p.patient_id}")
    return new


@router.get("/prescriptions/", response_model=List[schemas.Prescription])
def list_prescriptions(patient_id: int = None, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Doctor", "Admin", "Reception"))):
    q = db.query(Prescription)
    if patient_id:
        q = q.filter(Prescription.patient_id == patient_id)
    return q.all()


@router.post("/prescriptions/{presc_id}/fulfill")
def fulfill_prescription(presc_id: int, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Reception", "Pharmacist", "Admin"))):
    presc = db.query(Prescription).filter(Prescription.id == presc_id).first()
    if not presc: raise HTTPException(status_code=404, detail="Prescription not found")
    presc.fulfilled = True
    db.commit()
    db.refresh(presc)
    log_action(user.id, f"Fulfilled prescription {presc_id}")
    return presc


# --- Consent management ---
@router.post("/consents/", response_model=schemas.Consent)
def grant_consent(c: schemas.ConsentCreate, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Admin", "Reception", "Doctor"))):
    new = Consent(patient_id=c.patient_id, granted_to=c.granted_to, scope=c.scope, revoked=False, timestamp=datetime.utcnow())
    db.add(new)
    db.commit()
    db.refresh(new)

    # record consent on lightweight blockchain (encrypted)
    try:
        blockchain.new_transaction(sender=str(user.id), recipient=str(c.patient_id), amount=0, data={"type": "consent", "consent_id": new.id, "granted_to": c.granted_to})
    except Exception:
        pass

    log_action(user.id, f"Granted consent {new.id} for patient {c.patient_id}")
    return new


@router.post("/consents/{consent_id}/revoke")
def revoke_consent(consent_id: int, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Admin", "Doctor"))):
    cons = db.query(Consent).filter(Consent.id == consent_id).first()
    if not cons: raise HTTPException(status_code=404, detail="Consent not found")
    cons.revoked = True
    db.commit()
    db.refresh(cons)
    try:
        blockchain.new_transaction(sender=str(user.id), recipient=str(cons.patient_id), amount=0, data={"type": "consent_revoke", "consent_id": cons.id})
    except Exception:
        pass
    log_action(user.id, f"Revoked consent {consent_id}")
    return cons

# --- Patients ---
@router.post("/patients/", response_model=schemas.Patient)
def create_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db),
                   user: Staff = Depends(require_roles("Reception", "Admin"))):
    new_patient = Patient(name=patient.name, email=patient.email)
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    log_action(user.id, f"Created patient {new_patient.id} - {new_patient.name}")
    return new_patient


# Public patient registration
@router.post("/patients/register", response_model=schemas.Patient)
def register_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db)):
    existing_patient = db.query(Patient).filter(Patient.email == patient.email).first()
    if existing_patient:
        # Patient profiles created before portal access did not have credentials.
        # Let their first portal sign-up activate that existing profile, without
        # creating a duplicate clinical record.
        if not existing_patient.hashed_password and patient.password:
            existing_patient.hashed_password = get_password_hash(patient.password)
            db.commit()
            db.refresh(existing_patient)
            return existing_patient
        raise HTTPException(status_code=409, detail="An account already exists for this email")
    new_patient = Patient(name=patient.name, email=patient.email, hashed_password=get_password_hash(patient.password) if patient.password else None)
    # handle basic insurance creation if provided
    if patient.insurance_provider or patient.insurance_policy_number:
        from models import Insurance
        ins = Insurance(provider=patient.insurance_provider, policy_number=patient.insurance_policy_number)
        db.add(ins)
        db.commit()
        db.refresh(ins)
        new_patient.insurance = ins

    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient

@router.post("/patients/token", response_model=schemas.Token)
def patient_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.email == form_data.username).first()
    if not patient or not patient.hashed_password or not verify_password(form_data.password, patient.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": create_access_token({"patient_id": patient.id, "account_type": "patient"}), "token_type": "bearer"}


@router.get("/patients/", response_model=List[schemas.Patient])
def list_patients(db: Session = Depends(get_db), user: Staff = Depends(require_roles("Reception", "Doctor", "Admin"))):
    """Return the patient directory for authenticated clinical staff."""
    return db.query(Patient).order_by(Patient.name.asc()).all()

# --- Appointments ---
def is_doctor_available(db: Session, doctor_id: int, date):
    return not db.query(Appointment).filter(Appointment.doctor_id==doctor_id, Appointment.date==date).first()

def is_patient_available(db: Session, patient_id: int, date):
    return not db.query(Appointment).filter(Appointment.patient_id==patient_id, Appointment.date==date).first()

@router.post("/appointments/", response_model=schemas.Appointment)
def create_appointment(appt: schemas.AppointmentCreate, db: Session = Depends(get_db),
                       user: Staff = Depends(require_roles("Reception", "Doctor"))):
    if not is_doctor_available(db, appt.doctor_id, appt.date):
        raise HTTPException(status_code=400, detail="Doctor not available at this time")
    if not is_patient_available(db, appt.patient_id, appt.date):
        raise HTTPException(status_code=400, detail="Patient has a conflicting appointment")
    
    new_appt = Appointment(**appt.dict())
    db.add(new_appt)
    db.commit()
    db.refresh(new_appt)

    log_action(user.id, f"Created appointment {new_appt.id} for patient {appt.patient_id} with doctor {appt.doctor_id}")
    return new_appt

@router.post("/patient/appointments/", response_model=schemas.Appointment)
def book_patient_appointment(appt: schemas.PatientAppointmentCreate, db: Session = Depends(get_db), patient: Patient = Depends(get_current_patient)):
    if not db.query(Doctor).filter(Doctor.id == appt.doctor_id).first():
        raise HTTPException(status_code=404, detail="Doctor not found")
    if appt.service_id and not db.query(Service).filter(Service.id == appt.service_id).first():
        raise HTTPException(status_code=404, detail="Service not found")
    if not is_doctor_available(db, appt.doctor_id, appt.date):
        raise HTTPException(status_code=400, detail="Doctor is not available at this time")
    if not is_patient_available(db, patient.id, appt.date):
        raise HTTPException(status_code=400, detail="You already have an appointment at this time")
    booking = Appointment(patient_id=patient.id, doctor_id=appt.doctor_id, service_id=appt.service_id, date=appt.date)
    db.add(booking); db.commit(); db.refresh(booking)
    return booking

@router.get("/patient/appointments/", response_model=List[schemas.Appointment])
def list_patient_appointments(db: Session = Depends(get_db), patient: Patient = Depends(get_current_patient)):
    return db.query(Appointment).filter(Appointment.patient_id == patient.id).order_by(Appointment.date.desc()).all()

@router.get("/patient/billing/", response_model=List[schemas.Billing])
def list_patient_billing(db: Session = Depends(get_db), patient: Patient = Depends(get_current_patient)):
    """A patient can only see billing records attached to their own profile."""
    return db.query(Billing).filter(Billing.patient_id == patient.id).order_by(Billing.id.desc()).all()

@router.post("/patient/payments/simulate")
def pay_patient_bill(billing_id: int = Body(...), db: Session = Depends(get_db), patient: Patient = Depends(get_current_patient)):
    bill = db.query(Billing).filter(Billing.id == billing_id, Billing.patient_id == patient.id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Billing record not found")
    if bill.status == "paid":
        raise HTTPException(status_code=400, detail="This bill has already been paid")

    blockchain.new_transaction(
        sender=str(patient.id), recipient="hospital", amount=bill.amount or 0,
        data={"type": "patient_payment", "billing_id": bill.id},
    )
    last_proof = blockchain.last_block["proof"]
    proof = blockchain.proof_of_work(last_proof)
    blockchain.new_transaction("0", "miner", 1, data={"reward": "mined"})
    block = blockchain.new_block(proof, blockchain.hash(blockchain.last_block))
    bill.status = "paid"
    db.commit()
    return {"message": "Payment confirmed", "billing_id": bill.id, "block_index": block["index"]}


@router.get("/appointments/", response_model=List[schemas.Appointment])
def list_appointments(patient_id: int = None, doctor_id: int = None, db: Session = Depends(get_db), user: Staff = Depends(get_current_user)):
    q = db.query(Appointment)
    if patient_id:
        q = q.filter(Appointment.patient_id == patient_id)
    if doctor_id:
        q = q.filter(Appointment.doctor_id == doctor_id)
    return q.all()


@router.put("/appointments/{appt_id}/cancel", response_model=schemas.Appointment)
def cancel_appointment(appt_id: int, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Reception", "Doctor", "Admin"))):
    appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
    if not appt: raise HTTPException(status_code=404, detail="Appointment not found")
    appt.status = "cancelled"
    db.commit()
    db.refresh(appt)
    log_action(user.id, f"Cancelled appointment {appt_id}")
    return appt


@router.post("/doctors/{doc_id}/availability", response_model=schemas.DoctorAvailability)
def set_doctor_availability(doc_id: int, avail: schemas.DoctorAvailabilityCreate, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Admin", "Doctor"))):
    from models import DoctorAvailability
    new = DoctorAvailability(doctor_id=doc_id, start_time=avail.start_time, end_time=avail.end_time)
    db.add(new)
    db.commit()
    db.refresh(new)
    log_action(user.id, f"Set availability for doctor {doc_id}")
    return new


@router.get("/doctors/{doc_id}/availability", response_model=List[schemas.DoctorAvailability])
def get_doctor_availability(doc_id: int, db: Session = Depends(get_db), user: Staff = Depends(get_current_user)):
    from models import DoctorAvailability
    entries = db.query(DoctorAvailability).filter(DoctorAvailability.doctor_id == doc_id).all()
    return entries

# --- Billing ---
@router.post("/billing/", response_model=schemas.Billing)
def create_bill(bill: schemas.BillingCreate, db: Session = Depends(get_db),
                user: Staff = Depends(require_roles("Reception", "Admin"))):
    new_bill = Billing(**bill.dict())
    db.add(new_bill)
    db.commit()
    db.refresh(new_bill)

    log_action(user.id, f"Created billing {new_bill.id} for patient {bill.patient_id}")
    return new_bill

@router.post("/payments/")
def pay(amount: float, user: Staff = Depends(require_roles("Reception", "Admin"))):
    client_secret = create_payment_intent(amount)
    log_action(user.id, f"Initiated payment of amount ${amount}")
    return {"client_secret": client_secret}

@router.post("/billing/{bill_id}/insurance")
def submit_insurance_claim(bill_id: int, db: Session = Depends(get_db),
                           user: Staff = Depends(require_roles("Admin"))):
    bill = db.query(Billing).filter(Billing.id == bill_id).first()
    if bill is None: raise HTTPException(status_code=404, detail="Bill not found")
    if not bill.patient.insurance:
        raise HTTPException(status_code=400, detail="Patient has no insurance")
    
    bill.status = "insurance_pending"
    db.commit()

    log_action(user.id, f"Submitted insurance claim for billing {bill_id}")
    return bill

# --- EHR ---
@router.post("/ehr/", response_model=schemas.EHR)
def create_ehr(ehr: schemas.EHRCreate, db: Session = Depends(get_db),
               user: Staff = Depends(require_roles("Doctor"))):
    new_ehr = EHR(**ehr.dict())
    db.add(new_ehr)
    db.commit()
    db.refresh(new_ehr)

    # Record creation of EHR on the application audit log and the lightweight blockchain
    log_action(user.id, f"Created EHR {new_ehr.id} for patient {ehr.patient_id}")
    try:
        blockchain.new_transaction(
            sender="system",
            recipient=str(new_ehr.patient_id),
            amount=0,
            data={"type": "EHR", "ehr_id": new_ehr.id, "diagnosis": ehr.diagnosis},
        )
    except Exception:
        # Do not fail the main request if blockchain recording fails; just continue
        pass

    # create an initial EHR version for audit
    try:
        from models import EHRVersion
        from datetime import datetime as _dt
        ver = EHRVersion(ehr_id=new_ehr.id, patient_id=new_ehr.patient_id, diagnosis=new_ehr.diagnosis, medication=new_ehr.medication, notes=new_ehr.notes, timestamp=_dt.utcnow(), created_by=user.id)
        db.add(ver)
        db.commit()
        db.refresh(ver)
        # anchor the block containing the EHR tx if possible
        try:
            # mine to include tx
            last_proof = blockchain.last_block['proof']
            proof = blockchain.proof_of_work(last_proof)
            blockchain.new_transaction("0", "miner", 1, data={"reward": "mined"})
            previous_hash = blockchain.hash(blockchain.last_block)
            block = blockchain.new_block(proof, previous_hash)
            anchor = blockchain.anchor_block(block['index'])
            ver.anchor_id = anchor.get('anchor_id')
            db.commit()
            db.refresh(ver)
        except Exception:
            pass
    except Exception:
        db.rollback()

    return new_ehr


@router.get("/ehr/{ehr_id}", response_model=schemas.EHR)
def get_ehr(ehr_id: int, db: Session = Depends(get_db), user: Staff = Depends(get_current_user)):
    ehr = db.query(EHR).filter(EHR.id == ehr_id).first()
    if not ehr:
        raise HTTPException(status_code=404, detail="EHR not found")

    # Enforce consent: Admins and Doctors may view EHRs by role; others require explicit consent
    user_roles = [r.name for r in user.roles]
    if 'Admin' in user_roles or 'Doctor' in user_roles:
        return ehr

    # Check for explicit consent granted to this staff member for the patient
    consent = db.query(Consent).filter(Consent.patient_id == ehr.patient_id, Consent.granted_to == f'provider:{user.id}', Consent.revoked == False).first()
    if consent:
        return ehr

    raise HTTPException(status_code=403, detail="Access denied: no consent found")


@router.get("/patients/{patient_id}/ehr", response_model=List[schemas.EHR])
def get_patient_ehrs(patient_id: int, db: Session = Depends(get_db), user: Staff = Depends(get_current_user)):
    # Enforce consent similar to single EHR: Admins and Doctors may view; others require provider-specific consent
    user_roles = [r.name for r in user.roles]
    if 'Admin' in user_roles or 'Doctor' in user_roles:
        records = db.query(EHR).filter(EHR.patient_id == patient_id).all()
        return records

    consent = db.query(Consent).filter(Consent.patient_id == patient_id, Consent.granted_to == f'provider:{user.id}', Consent.revoked == False).first()
    if consent:
        records = db.query(EHR).filter(EHR.patient_id == patient_id).all()
        return records

    raise HTTPException(status_code=403, detail="Access denied: no consent found for patient")


@router.put("/ehr/{ehr_id}", response_model=schemas.EHR)
def update_ehr(ehr_id: int, ehr_in: schemas.EHRCreate, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Doctor"))):
    ehr = db.query(EHR).filter(EHR.id == ehr_id).first()
    if not ehr: raise HTTPException(status_code=404, detail="EHR not found")
    ehr.diagnosis = ehr_in.diagnosis
    ehr.medication = ehr_in.medication
    ehr.notes = ehr_in.notes
    db.commit()
    db.refresh(ehr)
    try:
        blockchain.new_transaction(
            sender=str(user.id),
            recipient=str(ehr.patient_id),
            amount=0,
            data={"type": "EHR_update", "ehr_id": ehr.id}
        )
    except Exception:
        pass
    return ehr


@router.get("/ehr/{ehr_id}/versions", response_model=List[schemas.EHRVersion])
def list_ehr_versions(ehr_id: int, db: Session = Depends(get_db), user: Staff = Depends(get_current_user)):
    # only Doctors/Admin or a provider with consent can view versions
    user_roles = [r.name for r in user.roles]
    ehr = db.query(EHR).filter(EHR.id == ehr_id).first()
    if not ehr:
        raise HTTPException(status_code=404, detail="EHR not found")
    if 'Admin' in user_roles or 'Doctor' in user_roles:
        versions = db.query(EHRVersion).filter(EHRVersion.ehr_id == ehr_id).order_by(EHRVersion.timestamp.desc()).all()
        return versions

    consent = db.query(Consent).filter(Consent.patient_id == ehr.patient_id, Consent.granted_to == f'provider:{user.id}', Consent.revoked == False).first()
    if consent:
        versions = db.query(EHRVersion).filter(EHRVersion.ehr_id == ehr_id).order_by(EHRVersion.timestamp.desc()).all()
        return versions

    raise HTTPException(status_code=403, detail="Access denied: no consent found for versions")

# --- Staff & Roles ---
@router.post("/roles/", response_model=schemas.Role)
def create_role(role: schemas.RoleCreate, db: Session = Depends(get_db),
                user: Staff = Depends(require_roles("Admin"))):
    new_role = Role(**role.dict())
    db.add(new_role)
    db.commit()
    db.refresh(new_role)

    log_action(user.id, f"Created role {new_role.id} - {new_role.name}")
    return new_role

@router.post("/staff/", response_model=schemas.Staff)
def create_staff(staff: schemas.StaffCreate, db: Session = Depends(get_db),
                 user: Staff = Depends(require_roles("Admin"))):
    from utils import get_password_hash
    hashed = get_password_hash(staff.password)
    new_staff = Staff(name=staff.name, email=staff.email, hashed_password=hashed)
    if staff.role_ids:
        roles = db.query(Role).filter(Role.id.in_(staff.role_ids)).all()
        new_staff.roles = roles
    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)

    log_action(user.id, f"Created staff {new_staff.id} - {new_staff.name}")
    return new_staff


# Staff management endpoints
@router.get("/staff/", response_model=List[schemas.Staff])
def list_staff(db: Session = Depends(get_db), user: Staff = Depends(require_roles("Admin"))):
    staff_members = db.query(Staff).all()
    return staff_members


@router.get("/staff/{staff_id}", response_model=schemas.Staff)
def get_staff(staff_id: int, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Admin"))):
    s = db.query(Staff).filter(Staff.id == staff_id).first()
    if not s: raise HTTPException(status_code=404, detail="Staff not found")
    return s


@router.put("/staff/{staff_id}", response_model=schemas.Staff)
def update_staff(staff_id: int, staff_update: schemas.StaffUpdate, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Admin"))):
    s = db.query(Staff).filter(Staff.id == staff_id).first()
    if not s: raise HTTPException(status_code=404, detail="Staff not found")
    if staff_update.name is not None:
        s.name = staff_update.name
    if staff_update.email is not None:
        s.email = staff_update.email
    if staff_update.role_ids is not None:
        roles = db.query(Role).filter(Role.id.in_(staff_update.role_ids)).all()
        s.roles = roles
    if staff_update.password:
        from utils import get_password_hash
        s.hashed_password = get_password_hash(staff_update.password)
    db.commit()
    db.refresh(s)
    log_action(user.id, f"Updated staff {staff_id}")
    return s


@router.delete("/staff/{staff_id}")
def delete_staff(staff_id: int, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Admin"))):
    s = db.query(Staff).filter(Staff.id == staff_id).first()
    if not s: raise HTTPException(status_code=404, detail="Staff not found")
    db.delete(s)
    db.commit()
    log_action(user.id, f"Deleted staff {staff_id}")
    return {"message": "deleted"}


# --- Doctors CRUD ---
@router.post("/doctors/", response_model=schemas.Doctor)
def create_doctor(doctor: schemas.DoctorCreate, db: Session = Depends(get_db),
                  user: Staff = Depends(require_roles("Admin"))):
    new_doc = Doctor(name=doctor.name, specialty=doctor.specialty)
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    log_action(user.id, f"Created doctor {new_doc.id} - {new_doc.name}")
    return new_doc


@router.get("/doctors/", response_model=List[schemas.Doctor])
def list_doctors(db: Session = Depends(get_db)):
    docs = db.query(Doctor).all()
    return docs

@router.get("/services/", response_model=List[schemas.Service])
def list_services(db: Session = Depends(get_db)):
    return db.query(Service).order_by(Service.name.asc()).all()

@router.post("/services/", response_model=schemas.Service)
def create_service(service: schemas.ServiceCreate, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Admin"))):
    new_service = Service(**service.dict())
    db.add(new_service); db.commit(); db.refresh(new_service)
    return new_service

@router.put("/services/{service_id}", response_model=schemas.Service)
def update_service(service_id: int, service: schemas.ServiceCreate, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Admin"))):
    current = db.query(Service).filter(Service.id == service_id).first()
    if not current: raise HTTPException(status_code=404, detail="Service not found")
    current.name, current.description, current.duration_minutes = service.name, service.description, service.duration_minutes
    db.commit(); db.refresh(current)
    return current

@router.delete("/services/{service_id}")
def delete_service(service_id: int, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Admin"))):
    current = db.query(Service).filter(Service.id == service_id).first()
    if not current: raise HTTPException(status_code=404, detail="Service not found")
    db.delete(current); db.commit()
    return {"message": "deleted"}


@router.get("/doctors/{doc_id}", response_model=schemas.Doctor)
def get_doctor(doc_id: int, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Reception", "Doctor", "Admin"))):
    doc = db.query(Doctor).filter(Doctor.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Doctor not found")
    return doc


@router.put("/doctors/{doc_id}", response_model=schemas.Doctor)
def update_doctor(doc_id: int, doctor: schemas.DoctorCreate, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Admin"))):
    doc = db.query(Doctor).filter(Doctor.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Doctor not found")
    doc.name = doctor.name
    doc.specialty = doctor.specialty
    db.commit()
    db.refresh(doc)
    log_action(user.id, f"Updated doctor {doc_id}")
    return doc


@router.delete("/doctors/{doc_id}")
def delete_doctor(doc_id: int, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Admin"))):
    doc = db.query(Doctor).filter(Doctor.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Doctor not found")
    db.delete(doc)
    db.commit()
    log_action(user.id, f"Deleted doctor {doc_id}")
    return {"message": "deleted"}

# --- Inventory ---
@router.post("/inventory/", response_model=schemas.Inventory)
def add_inventory(item: schemas.InventoryCreate, db: Session = Depends(get_db),
                  user: Staff = Depends(require_roles("Admin"))):
    new_item = Inventory(**item.dict())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    log_action(user.id, f"Added inventory item {new_item.id} - {new_item.name}")
    return new_item

# --- Lab / Radiology ---
@router.post("/lab_tests/", response_model=schemas.LabTest)
def order_lab_test(test: schemas.LabTestCreate, db: Session = Depends(get_db),
                   user: Staff = Depends(require_roles("Doctor"))):
    new_test = LabTest(**test.dict())
    db.add(new_test)
    db.commit()
    db.refresh(new_test)

    log_action(user.id, f"Ordered lab test {new_test.id} for patient {test.patient_id}")
    return new_test

@router.put("/lab_tests/{test_id}/result", response_model=schemas.LabTest)
def update_lab_result(test_id: int, result: str, db: Session = Depends(get_db),
                      user: Staff = Depends(require_roles("Lab Technician"))):
    test = db.query(LabTest).filter(LabTest.id == test_id).first()
    if not test: raise HTTPException(status_code=404, detail="Lab test not found")
    test.result = result
    test.status = "completed"
    db.commit()
    db.refresh(test)

    log_action(user.id, f"Updated lab result for test {test_id}")
    return test

# --- Analytics ---
@router.get("/analytics/appointments_per_doctor")
def appointments_per_doctor(db: Session = Depends(get_db),
                            user: Staff = Depends(require_roles("Admin"))):
    data = db.query(Doctor.name, func.count(Appointment.id)).join(Appointment).group_by(Doctor.id).all()

    log_action(user.id, "Viewed analytics: appointments per doctor")
    return [{"doctor": name, "appointments": count} for name, count in data]

@router.get("/analytics/revenue_per_month")
def revenue_per_month(db: Session = Depends(get_db),
                      user: Staff = Depends(require_roles("Admin"))):
    data = db.query(extract("month", Billing.id).label("month"), func.sum(Billing.amount)).group_by("month").all()

    log_action(user.id, "Viewed analytics: revenue per month")
    return [{"month": int(month), "revenue": float(total)} for month, total in data]

# --- JWT Login ---
@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), 
                           db: Session = Depends(get_db)):
    user = db.query(Staff).filter(Staff.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    roles = [r.name for r in user.roles]
    access_token = create_access_token({"user_id": user.id, "roles": roles})

    log_action(user.id, "Logged in")
    return {"access_token": access_token, "token_type": "bearer"}


# No refresh token endpoints — JWT-only auth


# --- Blockchain Endpoints (lightweight) ---
@router.get("/blockchain/chain")
def get_chain():
    return blockchain.get_chain()


@router.post("/blockchain/transactions/new")
def create_transaction(tx: dict = Body(...), db: Session = Depends(get_db), user: Staff = Depends(require_roles("Reception", "Admin"))):
    data = tx.get('data')
    index = blockchain.new_transaction(
        tx.get('sender'), tx.get('recipient'), tx.get('amount', 0), data
    )

    # If the transaction represents a payment, attempt to mark billing as paid
    try:
        if isinstance(data, dict) and data.get('type') == 'payment' and data.get('billing_id'):
            bill_id = int(data.get('billing_id'))
            bill = db.query(Billing).filter(Billing.id == bill_id).first()
            if bill:
                bill.status = 'paid'
                db.commit()
                db.refresh(bill)
                log_action(user.id, f"Processed payment for billing {bill_id} via blockchain tx")
    except Exception:
        pass

    return {"message": f"Transaction will be added to Block {index}"}


@router.get("/blockchain/mine")
def mine_block():
    last_proof = blockchain.last_block['proof']
    proof = blockchain.proof_of_work(last_proof)
    # reward for mining
    blockchain.new_transaction("0", "miner", 1, data={"reward": "mined"})
    previous_hash = blockchain.hash(blockchain.last_block)
    block = blockchain.new_block(proof, previous_hash)
    return {"message": "New Block Forged", "block": block}


@router.post("/blockchain/anchor")
def anchor_block(block_index: int = Body(None), db: Session = Depends(get_db), user: Staff = Depends(require_roles("Admin", "Reception"))):
    """Simulate anchoring of a block to an external ledger by storing an anchor locally.
    Optionally provide `block_index`; otherwise the latest block is anchored."""
    try:
        anchor = blockchain.anchor_block(block_index)
    except IndexError:
        raise HTTPException(status_code=400, detail="Block index out of range")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    log_action(user.id, f"Anchored block {anchor['block_index']} with anchor id {anchor['anchor_id']}")
    return anchor


@router.post("/payments/simulate")
def simulate_payment(billing_id: int = Body(...), db: Session = Depends(get_db), user: Staff = Depends(require_roles("Reception", "Admin"))):
    bill = db.query(Billing).filter(Billing.id == billing_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Billing not found")

    # create payment transaction on blockchain
    tx_index = blockchain.new_transaction(
        sender=str(bill.patient_id),
        recipient="hospital",
        amount=bill.amount or 0,
        data={"type": "payment", "billing_id": bill.id}
    )

    # Immediately mine the block to simulate confirmation
    last_proof = blockchain.last_block['proof']
    proof = blockchain.proof_of_work(last_proof)
    blockchain.new_transaction("0", "miner", 1, data={"reward": "mined"})
    previous_hash = blockchain.hash(blockchain.last_block)
    block = blockchain.new_block(proof, previous_hash)

    # Mark billing as paid (simulation)
    try:
        bill.status = 'paid'
        db.commit()
        db.refresh(bill)
        log_action(user.id, f"Simulated payment for billing {bill.id} — block {block['index']}")
    except Exception:
        pass

    return {"message": "Payment simulated and block forged", "block": block, "billing_id": bill.id}


# --- Assistant (Ollama) proxy ---
@router.post("/assistant/chat")
def assistant_chat(body: dict = Body(...)):
    """Proxy a simple chat request to a local Ollama HTTP API (http://localhost:11434).

    Body JSON: { "messages": [{"role":"user","content":"..."}, ...], "model": "ollama/modelname" }
    Returns Ollama's JSON response or an error if Ollama is not reachable.
    """
    if requests is None:
        raise HTTPException(status_code=500, detail="Python package 'requests' is required for assistant proxy. Install with `pip install requests`.")

    messages = body.get('messages') or []
    model = body.get('model', 'llama2')

    # Build a single prompt from messages (simple concat); for richer behavior, send structured payload to Ollama if available
    prompt = "\n".join([f"{m.get('role','user')}: {m.get('content','')}" for m in messages])

    url = 'http://localhost:11434/api/generate'
    payload = {"model": model, "prompt": prompt}

    try:
        resp = requests.post(url, json=payload, timeout=30)
    except requests.exceptions.RequestException as exc:
        # network / connection error to Ollama
        raise HTTPException(status_code=502, detail=f"Ollama proxy connection error: {str(exc)}")

    # If we get a non-2xx response, return its status and body to aid debugging
    if not (200 <= resp.status_code < 300):
        text = resp.text[:1000]
        raise HTTPException(status_code=502, detail=f"Ollama returned status {resp.status_code}: {text}")

    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text}



@router.get("/assistant/health")
def assistant_health():
    """Check connectivity to local Ollama instance."""
    if requests is None:
        raise HTTPException(status_code=500, detail="Python package 'requests' not installed")
    url = 'http://localhost:11434/api/models'
    try:
        r = requests.get(url, timeout=5)
        if r.ok:
            try:
                return {"ok": True, "models": r.json()}
            except Exception:
                return {"ok": True, "raw": r.text}
        return {"ok": False, "status": r.status_code, "body": r.text[:1000]}
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Ollama health check failed: {str(exc)}")


# --- Receipts ---
@router.post("/receipts/", response_model=schemas.Receipt)
def create_receipt(r: schemas.ReceiptCreate, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Reception", "Admin"))):
    bill = db.query(Billing).filter(Billing.id == r.billing_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Billing not found")

    # create receipt
    from datetime import datetime as _dt
    receipt = None
    try:
        from models import Receipt
        receipt = Receipt(billing_id=r.billing_id, amount=r.amount, timestamp=_dt.utcnow())
        db.add(receipt)
        bill.status = 'paid'
        db.commit()
        db.refresh(receipt)

        # record receipt on chain and anchor
        try:
            blockchain.new_transaction(sender=str(bill.patient_id), recipient='hospital', amount=r.amount, data={"type": "receipt", "receipt_id": receipt.id, "billing_id": bill.id})
            # mine instantly for simulation
            last_proof = blockchain.last_block['proof']
            proof = blockchain.proof_of_work(last_proof)
            blockchain.new_transaction("0", "miner", 1, data={"reward": "mined"})
            previous_hash = blockchain.hash(blockchain.last_block)
            block = blockchain.new_block(proof, previous_hash)
            anchor = blockchain.anchor_block(block['index'])
            receipt.anchor_id = anchor.get('anchor_id')
            db.commit()
            db.refresh(receipt)
        except Exception:
            # non-fatal
            pass

        log_action(user.id, f"Created receipt {receipt.id} for billing {bill.id}")
    except Exception:
        db.rollback()
        raise

    return receipt


@router.get("/receipts/", response_model=List[schemas.Receipt])
def list_receipts(billing_id: int = None, db: Session = Depends(get_db), user: Staff = Depends(get_current_user)):
    q = db.query(Receipt)
    if billing_id:
        q = q.filter(Receipt.billing_id == billing_id)
    return q.all()
