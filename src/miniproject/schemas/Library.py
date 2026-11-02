#now we will create aschema for the library  which will contain the name id owner id reference address lat long address these basic info
from pydantic import BaseModel
from typing import Optional

class Library(BaseModel):
    id: Optional[int] = None
    name: str
    owner_id: int
    reference: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class LibraryCreate(BaseModel):
    name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

#we are using int in owner id beacuse we are assuming that the owner id is a foreign key to the user table and user id is an int so we are using int in owner id
    
    

#now we will create a schema for the book which will contain the name id author id library id and the status of the book

class Book(BaseModel):
    id: Optional[int] = None
    name: str
    author_id: int
    library_id: int
    status: str
    count: int
    remaining: int
    
    
    
    
