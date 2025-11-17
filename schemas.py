"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class AuthUser(BaseModel):
    """
    Auth users collection schema
    Collection name: "authuser" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password_hash: str = Field(..., description="Hashed password")
    role: str = Field("owner", description="Role in the organization: owner, admin, tech")
    is_active: bool = Field(True, description="Whether user is active")
    organization: Optional[str] = Field(None, description="Organization or company name")

class Job(BaseModel):
    """
    Jobs collection schema
    Collection name: "job"
    """
    title: str = Field(..., description="Job title or summary")
    customer_name: str = Field(..., description="Customer full name")
    customer_phone: str = Field(..., description="Customer phone number")
    address: str = Field(..., description="Service address")
    status: str = Field("scheduled", description="scheduled, en_route, in_progress, completed, cancelled")
    scheduled_at: Optional[str] = Field(None, description="ISO datetime for scheduled time")
    technician: Optional[str] = Field(None, description="Assigned technician name or ID")

class InventoryItem(BaseModel):
    """
    Inventory items collection schema
    Collection name: "inventoryitem"
    """
    sku: str = Field(..., description="Stock keeping unit")
    name: str = Field(..., description="Item name")
    quantity: int = Field(0, ge=0, description="Quantity on hand")
    unit_cost: float = Field(0, ge=0, description="Unit cost in local currency")
    location: Optional[str] = Field(None, description="Warehouse or van location")

# Legacy examples retained for reference
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
