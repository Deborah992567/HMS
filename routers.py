from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from database import get_db
from models import Patient, Doctor, Appointment, Billing, EHR, Staff, Role, Inventory, LabTest
import schemas
from utils import create_payment_intent, require_roles, get_current_user, verify_password, create_access_token
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

router = APIRouter()

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
    new_patient = Patient(name=patient.name, email=patient.email)
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

    return new_ehr


@router.get("/ehr/{ehr_id}", response_model=schemas.EHR)
def get_ehr(ehr_id: int, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Doctor", "Admin", "Reception"))):
    ehr = db.query(EHR).filter(EHR.id == ehr_id).first()
    if not ehr: raise HTTPException(status_code=404, detail="EHR not found")
    return ehr


@router.get("/patients/{patient_id}/ehr", response_model=List[schemas.EHR])
def get_patient_ehrs(patient_id: int, db: Session = Depends(get_db), user: Staff = Depends(require_roles("Doctor", "Admin", "Reception"))):
    records = db.query(EHR).filter(EHR.patient_id == patient_id).all()
    return records


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
def list_doctors(db: Session = Depends(get_db), user: Staff = Depends(require_roles("Reception", "Doctor", "Admin"))):
    docs = db.query(Doctor).all()
    return docs


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
