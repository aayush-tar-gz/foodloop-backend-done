from foodloop_app import db
from flask_security import UserMixin, RoleMixin
from sqlalchemy.orm import relationship
from sqlalchemy import Table, Column, Integer, ForeignKey
from datetime import datetime

metadata = db.metadata

roles_users = Table(
    "roles_users",
    metadata,
    db.Column("user_id", Integer(), ForeignKey("user.id")),
    db.Column("role_id", Integer(), ForeignKey("role.id")),
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String, nullable=False)
    active = db.Column(db.Boolean, default=True)
    city = db.Column(db.String)
    pincode = db.Column(db.String)
    contact = db.Column(db.String)
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)

    roles = relationship("Role", secondary=roles_users, back_populates="users")
    inventory_items = relationship("InventoryItem", back_populates="user")
    food_requests = relationship("FoodRequest", back_populates="user")

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    users = relationship("User", secondary=roles_users, back_populates="roles")

class InventoryItem(db.Model):
    __tablename__ = 'inventory_item'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey("food.id"), nullable=False)

    food = db.relationship("Food", back_populates="inventory_items")
    user = db.relationship("User", back_populates="inventory_items")

class FoodRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inventory_item_id = db.Column(
        db.Integer, db.ForeignKey("inventory_item.id"), nullable=False
    )
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False)  # New field
    pickup_date = db.Column(db.DateTime)           # New field
    notes = db.Column(db.String)                   # New optional field
    status = db.Column(db.String, default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    inventory_item = relationship("InventoryItem")
    user = relationship("User", back_populates="food_requests")

class Food(db.Model):
    __tablename__ = 'food'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)
    is_refrigerated = db.Column(db.Boolean, default=False)
    quantity = db.Column(db.Float, nullable=False)
    best_before = db.Column(db.DateTime, nullable=False)  # New field
    expires_at = db.Column(db.DateTime, nullable=False)   # New field
    status = db.Column(db.String, default="Selling")      # New field
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    inventory_items = db.relationship("InventoryItem", back_populates="food")
