# foodloop_app/farmer_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_security.decorators import roles_required
from sqlalchemy import func, desc 
from datetime import datetime, timedelta
import google.generativeai as genai
from dotenv import load_dotenv
import os

from foodloop_app import db
from .models import User, FoodRequest, InventoryItem, Food

farmer_bp = Blueprint("farmer", __name__, url_prefix="/farmer")

load_dotenv()

@farmer_bp.route("/simple_demand_forecast", methods=["GET"])
@jwt_required()
def get_simple_demand_forecast():

    current_user_email = get_jwt_identity()
    farmer_user = User.query.filter_by(email=current_user_email).first()

    if not farmer_user:
        return jsonify({"error": "Farmer user not found"}), 404

    farmer_pincode = farmer_user.pincode
    if not farmer_pincode:
         return jsonify({"message": "Farmer profile requires a pincode to provide regional insights."}), 200

    # Define the time threshold for the latest 4 months
    four_months_ago = datetime.utcnow() - timedelta(days=120) # Approximately 4 months

    # --- 1. Query All Historical Demand Data (NGO Requests) for the pincode ---
    try:
        all_demanded_foods_data_query = db.session.query(
            Food.name,
            func.sum(FoodRequest.quantity).label('total_requested_quantity'),
            FoodRequest.created_at
        ).join(InventoryItem, FoodRequest.inventory_item_id == InventoryItem.id
        ).join(Food, InventoryItem.food_id == Food.id).join(User, InventoryItem.user_id == User.id).filter(User.pincode == farmer_pincode).group_by(Food.name, FoodRequest.created_at).order_by(FoodRequest.created_at.asc()).all() # Order by date to easily find oldest

        all_demanded_foods_data = [{"name": item.name, "total_requested_quantity": item.total_requested_quantity, "created_at": item.created_at} for item in all_demanded_foods_data_query]


        # --- 2. Handle Case: No Data ---
        if not all_demanded_foods_data:
            # No market data found at all
            return jsonify({
                "top_demanded_foods": [],
                "demand_forecast_text": "No market data available for this region.",
                "data_source": "none" # Indicate no data
            }), 200

        # --- 3. Data Exists: Determine Time Range and Filter if necessary ---
        oldest_data_date = all_demanded_foods_data[0]['created_at'] # Since we ordered by asc

        if oldest_data_date < four_months_ago:
            recent_demanded_foods_data = [
                item for item in all_demanded_foods_data
                if item['created_at'] >= four_months_ago
            ]
            data_for_analysis = recent_demanded_foods_data
            data_source_message = "Analysis based on the latest 4 months of market data."
        else:
            # Data is within the last 4 months, use all available data
            data_for_analysis = all_demanded_foods_data
            data_source_message = "Analysis based on all available recent market data."

        if not data_for_analysis:
             return jsonify({
                "top_demanded_foods": [],
                "demand_forecast_text": "No recent market data available for analysis.",
                "data_source": "none_recent" # Indicate no recent data
            }), 200


        # --- 4. Aggregate Data for Analysis Prompt (Sum quantities per food item within the selected range) ---
        aggregated_data = {}
        for item in data_for_analysis:
            food_name = item['name']
            quantity = item['total_requested_quantity']
            if food_name in aggregated_data:
                aggregated_data[food_name] += quantity
            else:
                aggregated_data[food_name] = quantity

        sorted_aggregated_data = sorted(aggregated_data.items(), key=lambda item: item[1], reverse=True)[:5] # Get top 5

        data_summary_for_gemini = f"Market data from pincode {farmer_pincode} over the relevant period:\n"
        if sorted_aggregated_data:
             for name, quantity in sorted_aggregated_data:
                data_summary_for_gemini += f"- {name}: {quantity:.1f}kg\n"
        else:
             data_summary_for_gemini += "No specific food item data available in the selected period (quantities might be zero or data structure issue)."


        # --- 5. Construct Simple Prompt for Gemini ---
        gemini_prompt = f"""
Analyze the following market data from a specific region (pincode {farmer_pincode}):
{data_summary_for_gemini}
Provide a very brief insight into what this data indicates about local demand and a simple text forecast or suggestion for farmers in this region regarding these top items. Keep it concise, a paragraph or a few bullet points.
"""

        # --- 6. Call Gemini API ---
        demand_forecast_text = "Could not get forecast insights."
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            if os.getenv("GEMINI_API_KEY"):
                model = genai.GenerativeModel('gemini-1.5-pro')
                gemini_response = model.generate_content(gemini_prompt)
                demand_forecast_text = gemini_response.text.strip()
            else:
                 demand_forecast_text = "AI service is not configured (API key missing)."

        except Exception as e:
            # Catch any error during Gemini call (API issues, network etc.)
            print(f"Error calling Gemini API: {e}")
            demand_forecast_text = f"Failed to get AI insights: {e}"

        # --- 7. Prepare Top Demanded Foods for Frontend Display (based on the data used for analysis) ---
        aggregated_for_display = {}
        for item in data_for_analysis:
             food_name = item['name']
             quantity = item['total_requested_quantity']
             if food_name in aggregated_for_display:
                 aggregated_for_display[food_name] += quantity
             else:
                 aggregated_for_display[food_name] = quantity

        top_foods_list = [{"item_name": name, "total_requested_quantity": quantity} for name, quantity in sorted(aggregated_for_display.items(), key=lambda item: item[1], reverse=True)[:5]]


        # --- 8. Send Response to Frontend ---
        return jsonify({
            "top_demanded_foods": top_foods_list,
            "demand_forecast_text": demand_forecast_text,
            "data_source": "historical" # Indicate that historical data was used for analysis
        }), 200

    except Exception as e:
         print(f"Unexpected error in simple_demand_forecast: {e}")
         return jsonify({"error": f"An unexpected error occurred: {e}"}), 500
