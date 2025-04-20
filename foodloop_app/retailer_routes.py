# retailer_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import db, User, InventoryItem, FoodRequest, Food
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
import google.generativeai as genai
from dotenv import load_dotenv
import os
import re
import logging

retailer_bp = Blueprint("retailer", __name__, url_prefix="/retailers")
# Configure logging (ensure this is set up correctly in your app)
logging.basicConfig(level=logging.DEBUG) # Make sure level is DEBUG or INFO to see the logs
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

@retailer_bp.route("/inventory", methods=["GET"])
@jwt_required()
def get_inventory():
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    inventory = InventoryItem.query.filter_by(user_id=user.id).all()
    return jsonify(
        [
            {
                "id": item.id,
                "name": item.food.name,
                "quantity": item.food.quantity,
                "best_before": item.food.best_before.isoformat() if item.food.best_before else None,
                "expires_at": item.food.expires_at.isoformat() if item.food.expires_at else None,
                "status": item.food.status or "Selling",
                # This created_at is from the Food item, not the InventoryItem creation time
                "food_created_at": item.food.created_at.isoformat() if item.food.created_at else None,
                # You might also want to return the InventoryItem creation time if needed
                # "inventory_created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in inventory
            if item.food # Ensure food relationship is loaded
        ]
    )


@retailer_bp.route("/add_item", methods=["POST"])
@jwt_required()
def add_inventory_item():
    logger.debug("Received request to add inventory item.")
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    if not user:
        logger.warning(f"User with email {current_user_email} not found.")
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    logger.debug(f"Request JSON data: {data}")

    required_fields = ["name", "quantity"]
    if not all(field in data for field in required_fields):
        logger.warning(f"Missing required fields in request: {data}")
        return jsonify({"error": "Missing required fields (name or quantity)"}), 422

    # Validate quantity format and value early
    try:
        quantity = float(data["quantity"])
        if quantity <= 0:
            logger.warning(f"Invalid quantity received: {quantity}")
            return jsonify({"error": "Quantity must be greater than 0"}), 422
    except ValueError:
        logger.warning(f"Invalid quantity format received: {data.get('quantity')}")
        return jsonify({"error": "Invalid quantity format"}), 422

    item_name = data["name"].strip()
    input_quantity = quantity # Use the validated quantity
    logger.debug(f"Validated item_name: {item_name}, quantity: {input_quantity}")

    # --- Main logic starts here ---
    try:
        # --- CASE 1: Check if the Food item type already exists globally ---
        # We MUST check this first to avoid the UNIQUE constraint error on INSERT
        existing_food_type = Food.query.filter(Food.name.ilike(item_name)).first()
        logger.debug(f"Checking for existing food type '{item_name}': {'Found' if existing_food_type else 'Not Found'}")

        if existing_food_type:
            # The Food type exists. Now, does THIS retailer have an InventoryItem for it?
            existing_inventory_item = InventoryItem.query.filter_by(
                user_id=user.id,
                food_id=existing_food_type.id
            ).first()
            logger.debug(f"Checking for existing inventory item for user {user.id} and food type {existing_food_type.id}: {'Found' if existing_inventory_item else 'Not Found'}")


            if existing_inventory_item:
                # --- CASE 1a: Food type exists, AND retailer already stocks it ---
                logger.debug("Case 1a: Updating existing inventory item.")
                # Update the quantity on the existing Food record (Note: affects global quantity due to schema)
                existing_food_type.quantity += input_quantity
                db.session.commit()
                logger.debug(f"Updated quantity for existing inventory item ID {existing_inventory_item.id} ('{item_name}'). New global quantity: {existing_food_type.quantity}")
                return jsonify({
                   "id": existing_inventory_item.id, # Existing InventoryItem ID
                   "food_id": existing_food_type.id,
                   "name": existing_food_type.name,
                   "quantity": existing_food_type.quantity, # Global quantity
                   "best_before": existing_food_type.best_before.isoformat() if existing_food_type.best_before else None, # Shared dates
                   "expires_at": existing_food_type.expires_at.isoformat() if existing_food_type.expires_at else None, # Shared dates
                   "status": existing_food_type.status, # Shared status
                   "message": f"Added {input_quantity} to existing '{item_name}'. Total quantity: {existing_food_type.quantity}"
                }), 200 # OK for update

            else:
                # --- CASE 1b: Food type exists, BUT retailer does NOT stock it yet ---
                logger.debug("Case 1b: Creating new inventory item linked to existing food type.")
                # DO NOT create a new Food. Create a new InventoryItem linking this user to the *existing* Food.
                logger.debug(f"Food type '{item_name}' exists (Food ID: {existing_food_type.id}), but user {user.id} does not have an inventory item for it. Creating new inventory link.")

                # Add quantity to the existing Food object (updates global quantity)
                existing_food_type.quantity += input_quantity

                # Create the new InventoryItem linking to the existing Food
                new_item = InventoryItem(user_id=user.id, food_id=existing_food_type.id)
                db.session.add(new_item)
                db.session.commit() # Commit both quantity update (on Food) and new inventory item (InventoryItem)

                # Refresh the new_item to get its database-generated ID for the response
                db.session.refresh(new_item)

                logger.debug(f"Created new inventory item ID {new_item.id} for user {user.id} linking to existing food type '{item_name}' (ID: {existing_food_type.id}). Global quantity: {existing_food_type.quantity}")

                return jsonify({
                    "id": new_item.id, # This is the NEW InventoryItem ID for this user
                    "food_id": existing_food_type.id,
                    "name": existing_food_type.name,
                    "quantity": existing_food_type.quantity, # Still global quantity
                    "best_before": existing_food_type.best_before.isoformat() if existing_food_type.best_before else None,
                    "expires_at": existing_food_type.expires_at.isoformat() if existing_food_type.expires_at else None,
                    "status": existing_food_type.status,
                    "message": f"Added '{item_name}' to your inventory."
                }), 201 # Created a new inventory entry for this user

        else:
            # --- CASE 2: Food item type does NOT exist globally ---
            logger.debug("Case 2: Creating new food type and inventory item.")
            # Create a new Food item AND a new InventoryItem for this retailer.
            logger.debug(f"Food type '{item_name}' does not exist. Creating new food type and inventory item.")

            # Call Gemini API to get dates for this brand new food item type
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            if not os.getenv("GEMINI_API_KEY"):
                logger.error("Gemini API key not configured.")
                return jsonify({"error": "Gemini API key not configured"}), 500

            # --- Date calculation moved inside the function ---
            current_utc_datetime = datetime.utcnow()
            current_utc_date_str = current_utc_datetime.date().isoformat()
            today_utc_date = current_utc_datetime.date()
            seven_days_from_today_date = today_utc_date + timedelta(days=7)
            # --- End of moved date calculation ---

            logger.debug(f"Calculated current_utc_date_str: {current_utc_date_str}")
            logger.debug(f"Calculated seven_days_from_today_date: {seven_days_from_today_date}")

            prompt = f"Given a food item '{item_name}', the current date is {current_utc_date_str}, and the location is '{user.city}'. Considering typical storage conditions, temperature, and the current season in this region, provide an estimated 'best_before' and 'expires_at' date in the exact format 'best_before:YYYY-MM-DDTHH:MM:SS, expires_at:YYYY-MM-DDTHH:MM:SS'. Use 12:00:00 for the time component unless a specific time is highly relevant. Do not include any text outside of the specified format. If you cannot generate reasonable estimated dates, return 'ERROR: Unable to generate valid dates'."
            logger.debug(f"Gemini prompt: {prompt}")

            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content(prompt)

            logger.debug(f"Raw Gemini response text: {response.text}")

            result = response.text.strip()
            if result == "ERROR: Unable to generate valid dates":
                logger.warning("Gemini returned error for date generation.")
                return jsonify({"error": "Gemini failed to generate valid dates based on rules"}), 422

            match = re.search(r"best_before:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}),\s*expires_at:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", result)
            if not match:
                logger.error(f"Gemini response format mismatch. Expected 'best_before:YYYY-MM-DDTHH:MM:SS, expires_at:YYYY-MM-DDTHH:MM:SS', got: {result}")
                return jsonify({"error": f"Invalid Gemini response format. Expected 'best_before:YYYY-MM-DDTHH:MM:SS, expires_at:YYYY-MM-DDTHH:MM:SS', got: {result}"}), 422

            best_before_str = match.group(1)
            expires_at_str = match.group(2)
            logger.debug(f"Extracted best_before_str: {best_before_str}, expires_at_str: {expires_at_str}")

            # Validate dates from Gemini
            try:
                # Use fromisoformat with the timezone offset directly if present ('Z')
                best_before = datetime.fromisoformat(best_before_str.replace("Z", "+00:00"))
                expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                logger.debug(f"Parsed best_before datetime: {best_before}, expires_at datetime: {expires_at}")

            except ValueError as e:
                 logger.error(f"Date parsing error from Gemini output: {best_before_str}, {expires_at_str} - {str(e)}", exc_info=True)
                 return jsonify({"error": f"Error parsing dates from Gemini: {str(e)}"}), 500

            # --- USE THE NEWLY CALCULATED seven_days_from_today_date ---
            if best_before.date() < seven_days_from_today_date or expires_at < best_before + timedelta(days=14):
                 logger.warning(f"Generated dates are invalid based on rules. best_before: {best_before}, expires_at: {expires_at}, seven_days_from_today_date: {seven_days_from_today_date}")
                 return jsonify({"error": "Generated dates are invalid (best before must be at least 7 days from today, and expiry at least 14 days after best before)"}), 422

            # Create the NEW Food item (since it's a new type)
            # created_at should reflect the time THIS Food entry is created
            food = Food(
                name=item_name,
                quantity=input_quantity, # Initial quantity for this new type
                best_before=best_before, # Dates from Gemini
                expires_at=expires_at,    # Dates from Gemini
                created_at=datetime.utcnow(), # Use current UTC time for creation timestamp
                status="Selling"
                 # Add is_refrigerated if needed and available in data
            )
            db.session.add(food)
            db.session.flush() # Get food.id
            logger.debug(f"Created new Food object with ID: {food.id}, created_at: {food.created_at}")


            # Create the NEW InventoryItem linking the user to this new Food type
            new_item = InventoryItem(user_id=user.id, food_id=food.id)
            db.session.add(new_item)
            db.session.commit()
            logger.debug(f"Created new inventory item ID {new_item.id} for user {user.id} linking to new food type '{food.name}' (ID: {food.id}). Quantity: {food.quantity}")

            return jsonify({
                "id": new_item.id,
                "food_id": food.id,
                "name": food.name,
                "quantity": food.quantity,
                "best_before": food.best_before.isoformat() if food.best_before else None,
                "expires_at": food.expires_at.isoformat() if food.expires_at else None,
                "status": food.status,
                "food_created_at": food.created_at.isoformat() # Include the Food creation date in response
            }), 201 # Created new InventoryItem and Food

    except SQLAlchemyError as e:
        db.session.rollback() # Roll back the transaction on error
        logger.error(f"Database error adding inventory item: {e}", exc_info=True)
        return jsonify({"error": "Database error while adding item."}), 500
    except Exception as e:
        logger.error(f"Unexpected error adding inventory item: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@retailer_bp.route("/requested_food", methods=["GET"])
@jwt_required()
def get_food_requests():
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    requests = FoodRequest.query.join(InventoryItem).filter(InventoryItem.user_id == user.id).all()
    return jsonify([
        {
            "id": req.id,
            "food_id": req.inventory_item.food_id,
            "ngo_id": req.requester_id,
            "quantity": req.quantity if hasattr(req, "quantity") else req.inventory_item.food.quantity,
            "status": req.status,
            "pickup_date": req.pickup_date.isoformat() if req.pickup_date else None,
            "created_at": req.created_at.isoformat(),
        }
        for req in requests
    ])


@retailer_bp.route("/inventory/<int:id>/sell", methods=["POST"])
@jwt_required()
def sell_inventory_item(id):
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Find the specific InventoryItem belonging to this user
    item = InventoryItem.query.filter_by(id=id, user_id=user.id).first()
    if not item:
        return jsonify({"error": "Inventory item not found"}), 404

    data = request.get_json()
    if not data: # Check if data is even present
         return jsonify({"error": "Request body must be JSON"}), 415 # 415 Unsupported Media Type if not JSON
    if "quantity" not in data: # Check if quantity key exists
        return jsonify({"error": "Quantity is required"}), 422

    try:
        quantity_to_sell = float(data["quantity"])
        if quantity_to_sell <= 0:
            return jsonify({"error": "Quantity must be greater than 0"}), 422

        # Check if there's enough quantity in stock
        if quantity_to_sell > item.food.quantity:
            return jsonify({"error": "Insufficient quantity"}), 422

        current_date = datetime.utcnow()
        # FIX: Changed item.food.expiry_date to item.food.expires_at
        # This check means 'If current date is AFTER the expiration date...'
        if item.food.expires_at and current_date > item.food.expires_at:
             # Added check for expires_at being None just in case
            return jsonify({"error": "Cannot sell after expiry date"}), 422

        # Deduct the sold quantity from the stock
        item.food.quantity -= quantity_to_sell

        # If quantity drops to zero or less, you might want to change status,
        # though the requirement here is just to sell.
        # if item.food.quantity <= 0:
        #     item.food.status = "SoldOut" # Example

        db.session.commit()

        # Return the updated remaining quantity
        return jsonify({
            "message": f"Sold {quantity_to_sell} of {item.food.name}",
            "remaining_quantity": item.food.quantity
        }), 200

    except ValueError: # Catch if the "quantity" value cannot be converted to float
        db.session.rollback()
        return jsonify({"error": "Invalid quantity value format"}), 422
    except SQLAlchemyError as e: # Catch potential database errors during commit
        db.session.rollback()
        logger.error(f"Database error selling item {id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Database error occurred while selling item"}), 500
    except Exception as e: # Catch any other unexpected errors
        db.session.rollback()
        logger.error(f"Unexpected error selling item {id}: {str(e)}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@retailer_bp.route("/inventory/<int:id>/list", methods=["POST"])
@jwt_required()
def list_inventory_item(id):
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    item = InventoryItem.query.filter_by(id=id, user_id=user.id).first()
    if not item or item.food.quantity <= 0:
        return jsonify({"error": "Inventory item not found or no quantity available"}), 404

    current_date = datetime.utcnow()
    if current_date > item.food.expires_at:
        return jsonify({"error": "Food has already expired"}), 422
    
    item.food.status = "Listing"
    try:
        db.session.commit()
        return jsonify({"message": "Food listed for NGOs"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error listing item {id}: {str(e)}", exc_info=True)
        return jsonify({"error": "Database error occurred while listing item"}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error listing item {id}: {str(e)}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@retailer_bp.route("/notifications", methods=["GET"])
@jwt_required()
def get_notifications():
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Mock notifications (replace with actual logic or database table)
    inventory = InventoryItem.query.filter_by(user_id=user.id).all()
    notifications = []
    current_date = datetime.utcnow()
    for item in inventory:
        if item.food.quantity > 0 and item.food.status == "Selling" and current_date > item.food.expiry_date:
            notifications.append({
                "id": item.id,
                "message": f"Your {item.food.name} (remaining: {item.food.quantity}) is past best before. List it or ignore.",
                "options": ["List", "Ignore"]
            })

    return jsonify(notifications), 200

@retailer_bp.route("/requests/<int:request_id>/approve", methods=["POST"])
@jwt_required()
def approve_request(request_id):
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    request = FoodRequest.query.filter_by(id=request_id).first()
    if not request or request.inventory_item.user_id != user.id or request.status != "pending":
        return jsonify({"error": "Request not found or already processed"}), 404

    request.status = "approved"
    request.inventory_item.food.status = "Approved"
    db.session.commit()

    return jsonify({"message": "Request approved"}), 200

@retailer_bp.route("/requests/<int:request_id>/ignore", methods=["POST"])
@jwt_required()
def ignore_request(request_id):
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    request = FoodRequest.query.filter_by(id=request_id).first()
    if not request or request.inventory_item.user_id != user.id or request.status != "pending":
        return jsonify({"error": "Request not found or already processed"}), 404

    request.status = "ignored"
    db.session.commit()

    return jsonify({"message": "Request ignored"}), 200

# foodloop_app/retailer_routes.py
# ... (existing imports and blueprint definition remain the same)

@retailer_bp.route("/item/remove/<int:item_id>", methods=["DELETE"])
@jwt_required()
def remove_inventory_item(item_id):
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    if not user or "Retailer" not in [role.name for role in user.roles]:
        return jsonify({"error": "User not found or not a retailer"}), 404

    item = InventoryItem.query.filter_by(id=item_id, user_id=user.id).first()
    if not item:
        return jsonify({"error": "Inventory item not found"}), 404

    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Item removed successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@retailer_bp.route("/food/<int:id>/ignore", methods=["POST"])
@jwt_required()
def ignore_notification(id):
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()

    if not user or "Retailer" not in [role.name for role in user.roles]:
        return jsonify({"error": "User not found or not a retailer"}), 404

    item = InventoryItem.query.filter_by(id=id, user_id=user.id).join(Food).first()
    if not item or item.food.status not in ["Selling", "Listing"]:
        return jsonify({"error": "Item not found or not eligible for ignore"}), 404

    # No status change; simply acknowledge the ignore action
    # Optionally, log this action in a notifications table if implemented
    return jsonify({"message": "Notification ignored"}), 200
