from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from database import Base

# Many-to-Many Staff <-> Roles
staff_roles = Table(
    'staff_roles', Base.metadata,
    Column('staff_id', Integer, ForeignKey('staff.id')),
    Column('role_id', Integer, ForeignKey('roles.id'))
)

# --- Patients & Insurance ---
class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    insurance_id = Column(Integer, ForeignKey("insurance.id"))
    insurance = relationship("Insurance", back_populates="patient", uselist=False)
    appointments = relationship("Appointment", back_populates="patient")
    ehr_records = relationship("EHR", back_populates="patient")
    bills = relationship("Billing", back_populates="patient")
    lab_tests = relationship("LabTest", back_populates="patient")

class Insurance(Base):
    __tablename__ = "insurance"
    id = Column(Integer, primary_key=True)
    provider = Column(String)
    policy_number = Column(String, unique=True)
    patient = relationship("Patient", back_populates="insurance")

# --- Staff & Roles ---
class Staff(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    roles = relationship("Role", secondary=staff_roles, back_populates="staff_members")

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    staff_members = relationship("Staff", secondary=staff_roles, back_populates="roles")

# --- Doctors & Appointments ---
class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    specialty = Column(String)
    appointments = relationship("Appointment", back_populates="doctor")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    status = Column(String, default="scheduled")  # scheduled, cancelled, completed
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")


# --- Doctor Availability ---
class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"
    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    doctor = relationship("Doctor")

# --- Billing & Payments ---
class Billing(Base):
    __tablename__ = "billing"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    amount = Column(Float)
    status = Column(String, default="pending")  # pending, insurance_pending, paid, rejected
    patient = relationship("Patient", back_populates="bills")

# --- EHR ---
class EHR(Base):
    __tablename__ = "ehr"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    diagnosis = Column(String)
    medication = Column(String)
    notes = Column(String, nullable=True)
    patient = relationship("Patient", back_populates="ehr_records")

# --- Inventory ---
class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True)
    item_name = Column(String)
    quantity = Column(Integer)
    unit_price = Column(Float)

# --- Lab / Radiology ---
class LabTest(Base):
    __tablename__ = "lab_tests"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    test_name = Column(String)
    result = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, completed
    patient = relationship("Patient", back_populates="lab_tests")


# --- Prescriptions ---
class Prescription(Base):
    __tablename__ = "prescriptions"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    medication = Column(String)
    dosage = Column(String)
    instructions = Column(String)
    fulfilled = Column(Boolean, default=False)
    patient = relationship("Patient")
    doctor = relationship("Doctor")


# --- Consent ---
class Consent(Base):
    __tablename__ = "consents"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    granted_to = Column(String)  # e.g., 'research', 'provider:123'
    scope = Column(String)  # brief description
    revoked = Column(Boolean, default=False)
    timestamp = Column(DateTime)
    patient = relationship("Patient")

