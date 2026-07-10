from dataclasses import dataclass 
from app.domain.value_object.role import Role

@dataclass(frozen=True, slots=True)
class User: 
    id:str
    email:str
    role: Role
    department: str | None = None
    
