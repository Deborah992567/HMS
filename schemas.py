from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional



class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: int
    roles: list[str] = []


# --- Patient ---
class PatientBase(BaseModel):
    name: str
    email: EmailStr

class PatientCreate(PatientBase):
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None

class Patient(PatientBase):
    id: int
    class Config:
        orm_mode = True

# --- Appointment ---
class AppointmentBase(BaseModel):
    date: datetime
    patient_id: int
    doctor_id: int

class AppointmentCreate(AppointmentBase):
    pass

class Appointment(AppointmentBase):
    id: int
    class Config:
        orm_mode = True

# --- Doctor ---
class DoctorBase(BaseModel):
    name: str
    specialty: Optional[str] = None

class DoctorCreate(DoctorBase):
    pass

class Doctor(DoctorBase):
    id: int
    class Config:
        orm_mode = True

# --- Billing ---
class BillingBase(BaseModel):
    patient_id: int
    amount: float
    status: Optional[str] = "pending"

class BillingCreate(BillingBase):
    pass

class Billing(BillingBase):
    id: int
    class Config:
        orm_mode = True

# --- EHR ---
class EHRBase(BaseModel):
    patient_id: int
    diagnosis: str
    medication: str
    notes: Optional[str] = None

class EHRCreate(EHRBase):
    pass

class EHR(EHRBase):
    id: int
    class Config:
        orm_mode = True

# --- Staff / Role ---
class RoleBase(BaseModel):
    name: str

class RoleCreate(RoleBase):
    pass

class Role(RoleBase):
    id: int
    class Config:
        orm_mode = True

class StaffBase(BaseModel):
    name: str
    email: EmailStr

class StaffCreate(StaffBase):
    role_ids: List[int] = []
    password: str

class StaffUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role_ids: Optional[List[int]] = None
    password: Optional[str] = None

class Staff(StaffBase):
    id: int
    roles: List[Role] = []
    class Config:
        orm_mode = True

# --- Inventory ---
class InventoryBase(BaseModel):
    item_name: str
    quantity: int
    unit_price: float

class InventoryCreate(InventoryBase):
    pass

class Inventory(InventoryBase):
    id: int
    class Config:
        orm_mode = True

# --- Lab ---
class LabTestBase(BaseModel):
    patient_id: int
    test_name: str

class LabTestCreate(LabTestBase):
    pass

class LabTest(LabTestBase):
    id: int
    result: Optional[str]
    status: str
    class Config:
        orm_mode = True
