from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import db, User, InventoryItem, FoodRequest, Food
from sqlalchemy import and_
from datetime import datetime 
from sqlalchemy.exc import SQLAlchemyError
ngo_bp = Blueprint("ngo", __name__, url_prefix="/ngo")


@ngo_bp.route("/filtered_food", methods=["GET"])
@jwt_required()
def get_nearby_food():
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Filter items by the same pincode
    nearby_items = (
        InventoryItem.query.join(Food)
        .join(User)
        .filter(
            and_(
                Food.status == "Listing",
                User.pincode == user.pincode,
                Food.quantity > 0
            )
        )
        .all()
    )
    return jsonify(
        [
            {
                "id": item.id,
                "name": item.food.name,
                "quantity": item.food.quantity,
                "best_before": item.food.best_before.isoformat(),
                "expires_at": item.food.expires_at.isoformat(),
                "location": {"city": item.user.city, "pincode": item.user.pincode},
                "retailer_contact": item.user.contact,
            }
            for item in nearby_items
        ]
    )

@ngo_bp.route("/request", methods=["POST"])
@jwt_required()
def create_food_request():
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()

    try:
        # Get required fields directly. If 'inventory_item_id' or 'quantity'
        # are missing, this will raise a KeyError, caught below.
        # We'll rely on SQLAlchemy/DB to handle type conversion and NOT NULL checks
        # when we create the object and commit later.
        inventory_item_id = data["inventory_item_id"]
        quantity = data["quantity"]

        # Get optional fields safely using .get(), which returns None if the key is missing
        pickup_date_str = data.get("pickup_date")
        notes = data.get("notes")

        # Parse pickup_date string if provided - MUST handle potential ValueError here
        pickup_date = None
        if pickup_date_str:
            try:
                # Attempt to parse the ISO format date string
                # .replace("Z", "+00:00") handles potential UTC 'Z' suffix
                pickup_date = datetime.fromisoformat(pickup_date_str.replace("Z", "+00:00"))
            except ValueError:
                # If parsing fails, return a specific 422 error for the date format
                # This check is kept separate because the error message is specific and helpful
                return jsonify({"error": "Invalid pickup_date format. Use YYYY-MM-DDTHH:MM:SS"}), 422


        # Create the FoodRequest object using the data retrieved.
        # SQLAlchemy will handle converting data types (e.g., float for quantity)
        # and will check NOT NULL constraints when committed.
        new_request = FoodRequest(
            inventory_item_id=inventory_item_id,
            requester_id=user.id, # User ID is guaranteed from the JWT check
            quantity=quantity,
            pickup_date=pickup_date, # This will be a datetime object or None
            notes=notes,             # This will be a string or None
            status="pending",        # Set default status
            created_at=datetime.utcnow() # Set creation time
        )

        db.session.add(new_request)
        db.session.commit() # Database NOT NULL constraints are enforced here

        # Success response
        return jsonify(
            {
                "id": new_request.id,
                "message": "Food request created successfully",
                # Optional: return details of the created request
                # "inventory_item_id": new_request.inventory_item_id,
                # "quantity": new_request.quantity,
                # "pickup_date": new_request.pickup_date.isoformat() if new_request.pickup_date else None,
            }
        ), 201 # 201 Created


    # --- Error Handling ---
    # Catch errors if keys are missing (KeyError), values have wrong types (ValueError/TypeError during
    # object creation or commit), or database issues (SQLAlchemyError like NOT NULL).
    # This is a more general catch block for input/database issues.
    except (KeyError, ValueError, TypeError, SQLAlchemyError) as e:
        db.session.rollback() # Roll back the session on any error
        # Log the specific error for debugging server-side
        # Return a general client error. The message includes the specific DB error detail.
        return jsonify({"error": f"Failed to create food request. Please check your input. Details: {str(e)}"}), 400 # 400 Bad Request

    # Catch any other unexpected errors that might occur
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An unexpected internal error occurred: {str(e)}"}), 500 # 500 Internal Server Error


@ngo_bp.route("/my_requests", methods=["GET"])
@jwt_required()
def get_my_requests():
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    requests = FoodRequest.query.filter_by(requester_id=user.id).all()

    return jsonify(
        [
            {
                "id": req.id,
                "inventory_item": {
                    "id": req.inventory_item.id,
                    "name": req.inventory_item.food.name,
                    "quantity": req.inventory_item.food.quantity,
                },
                "status": req.status,
                "created_at": req.created_at.isoformat(),
            }
            for req in requests
        ]
    )
