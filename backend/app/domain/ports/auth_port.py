from abc import ABC, abstractmethod
from app.domain.entities.user import User

class AuthPort(ABC):
    @abstractmethod
    async def authenticate(self, email:str , password: str) -> User | None:...
    
    @abstractmethod
    async def get_user_by_id(self , user_id:str) -> User | None: ...

    @abstractmethod
    async def get_user_by_email(self , email:str) -> User | None: ...
    