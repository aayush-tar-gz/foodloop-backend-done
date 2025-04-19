# FoodLoop Backend API Documentation

This document outlines the API endpoints for the FoodLoop backend, built with Flask. The API supports user authentication, food inventory management, surplus food listing, and redistribution for retailers, NGOs, and admins, focusing on waste prevention using "best before" and "expires at" dates.

**Base URL**: `http://localhost:5000` (adjust based on deployment)

**Authentication**: Protected routes require a JWT token (valid for 1 day), obtained via the `/login` endpoint, included in the `Authorization` header as `Bearer <token>`.

---

## Summary Table

| Method   | Endpoint                          | Description                                      | Authentication |
| :------- | :-------------------------------- | :----------------------------------------------- | :------------- |
| `POST`   | `/sign-up`                        | Create a new user account                        | None           |
| `POST`   | `/login`                          | Authenticate user                                | None           |
| `POST`   | `/logout`                         | Log out the current user                         | None           |
| `GET`    | `/ngo/filtered_food`              | Get listed food items filtered by pincode        | NGO Required   |
| `POST`   | `/ngo/request/<int:id>`           | NGO requests a specific listed food item         | NGO Required   |
| `GET`    | `/ngo/my_requests`                | Get requests made by the authenticated NGO       | NGO Required   |
| `POST`   | `/ngo/claim/<int:id>`             | NGO claims a specific approved food item         | NGO Required   |
| `GET`    | `/retailers/inventory`            | Get authenticated retailer's food inventory      | Retailer Req.  |
| `POST`   | `/retailers/add_item`             | Add a new food item (batch) to inventory         | Retailer Req.  |
| `DELETE` | `/retailers/item/remove/<int:item_id>` | Remove an inventory item (batch)         | Retailer Req.  |
| `POST`   | `/retailers/inventory/<int:id>/sell` | Sell quantity from an inventory item     | Retailer Req.  |
| `POST`   | `/retailers/inventory/<int:id>/list` | Change item status to 'Listing'          | Retailer Req.  |
| `GET`    | `/retailers/notifications`        | Get notifications for the authenticated retailer | Retailer Req.  |
| `GET`    | `/retailers/requests`             | Get requests from NGOs for the retailer's food   | Retailer Req.  |
| `POST`   | `/retailers/requests/<int:request_id>/approve` | Approve an NGO's request         | Retailer Req.  |
| `POST`   | `/retailers/requests/<int:request_id>/ignore` | Ignore an NGO's request          | Retailer Req.  |
| `POST`   | `/retailers/food/<int:id>/ignore` | Ignore notification for an item                  | Retailer Req.  |
| `GET`    | `/admin/food`                     | Get all food items (Admin/Debug)                 | Admin Req.     |

---

## Authentication Routes

### Sign Up

**Create a new user account.**

- **Method**: POST
- **URL**: `/sign-up`
- **Authentication**: None
- **Content-Type**: `application/json`
- **Request Body**:

  ```json
  {
    "email": "string",
    "password": "string",
    "city": "string",
    "pincode": "string",
    "contact": "string",
    "role": "string" // One of: "Retailer", "Ngo", "Farmer", "Admin"
  }
  ```
- **Responses**:
  - **201 Created**:

    ```json
    {
      "message": "User created successfully"
    }
    ```
  - **409 Conflict**:

    ```json
    {
      "error": "Email address is already registered"
    }
    ```
  - **402 Bad Request**:

    ```json
    {
      "error": "Missing required fields"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "Invalid role: <role>"
    }
    ```
  - **500 Internal Server Error**:

    ```json
    {
      "error": "An error occurred during registration: <error>"
    }
    ```

### Login

**Authenticate a user and obtain a JWT token (valid for 1 day).**

- **Method**: POST
- **URL**: `/login`
- **Authentication**: None
- **Content-Type**: `application/json`
- **Request Body**:

  ```json
  {
    "email": "string",
    "password": "string"
  }
  ```
- **Responses**:
  - **200 OK**:

    ```json
    {
      "message": "Login successful",
      "token": "string",
      "user": {
        "id": integer,
        "email": "string",
        "city": "string",
        "pincode": "string",
        "contact": "string",
        "roles": ["string"]
      }
    }
    ```
  - **401 Unauthorized**:

    ```json
    {
      "error": "Invalid email or password"
    }
    ```
  - **402 Bad Request**:

    ```json
    {
      "error": "Email and password are required"
    }
    ```

### Logout

**Log out the current user.**

- **Method**: POST
- **URL**: `/logout`
- **Authentication**: None
- **Responses**:
  - **200 OK**:

    ```json
    {
      "message": "Logged out successfully"
    }
    ```

---

## NGO Routes

### Get Filtered Food

**Get listed food items filtered by the NGO's pincode.**

- **Method**: GET
- **URL**: `/ngo/filtered_food`
- **Authentication**: NGO Required
- **Query Parameters**:
  - `pincode` (optional, string): Filter by pincode (defaults to user's pincode)
- **Responses**:
  - **200 OK**:

    ```json
    [
      {
        "id": integer,
        "name": "string",
        "quantity": integer,
        "best_before": "string", // Format: YYYY-MM-DDTHH:MM:SS
        "expires_at": "string",  // Format: YYYY-MM-DDTHH:MM:SS
        "location": {
          "city": "string",
          "pincode": "string"
        },
        "retailer_contact": "string"
      }
    ]
    ```
  - **404 Not Found**:

    ```json
    {
      "error": "User not found or not an NGO"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "Unauthorized access"
    }
    ```

### Create Food Request

**NGO requests a specific listed food item.**

- **Method**: POST
- **URL**: `/ngo/request/<int:id>`
  - `<int:id>`: ID of the inventory item
- **Authentication**: NGO Required
- **Content-Type**: `application/json`
- **Request Body**:

  ```json
  {
    "quantity": "integer",
    "pickup_date": "string", // Optional, Format: YYYY-MM-DDTHH:MM:SS
    "notes": "string"       // Optional
  }
  ```
- **Responses**:
  - **201 Created**:

    ```json
    {
      "id": integer,
      "food_id": integer,
      "quantity": integer,
      "status": "pending",
      "pickup_date": "string", // Format: YYYY-MM-DDTHH:MM:SS or null
      "created_at": "string"   // Format: YYYY-MM-DDTHH:MM:SS
    }
    ```
  - **422 Unprocessable Entity**:

    ```json
    {
      "error": "Missing required fields (quantity)"
    }
    ```
  - **404 Not Found**:

    ```json
    {
      "error": "Item not found or not available for request"
    }
    ```
  - **400 Bad Request**:

    ```json
    {
      "error": "Requested quantity exceeds available amount"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "User not found or not an NGO"
    }
    ```

### Get My Requests

**Get requests made by the authenticated NGO.**

- **Method**: GET
- **URL**: `/ngo/my_requests`
- **Authentication**: NGO Required
- **Responses**:
  - **200 OK**:

    ```json
    [
      {
        "id": integer,
        "food_id": integer,
        "name": "string",
        "quantity": integer,
        "status": "string", // e.g., "pending", "approved", "completed"
        "pickup_date": "string", // Format: YYYY-MM-DDTHH:MM:SS or null
        "created_at": "string"   // Format: YYYY-MM-DDTHH:MM:SS
      }
    ]
    ```
  - **404 Not Found**:

    ```json
    {
      "error": "User not found or not an NGO"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "Unauthorized access"
    }
    ```

### Claim Food

**NGO claims a specific approved food item.**

- **Method**: POST
- **URL**: `/ngo/claim/<int:id>`
  - `<int:id>`: ID of the food request
- **Authentication**: NGO Required
- **Responses**:
  - **200 OK**:

    ```json
    {
      "message": "Food claimed successfully"
    }
    ```
  - **404 Not Found**:

    ```json
    {
      "error": "Request not found"
    }
    ```
  - **400 Bad Request**:

    ```json
    {
      "error": "Request not approved or food not available for claiming"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "User not found or not an NGO"
    }
    ```

---

## Retailer Routes

### Get Inventory

**Get authenticated retailer's food inventory.**

- **Method**: GET
- **URL**: `/retailers/inventory`
- **Authentication**: Retailer Required
- **Responses**:
  - **200 OK**:

    ```json
    [
      {
        "id": integer,
        "name": "string",
        "quantity": integer,
        "best_before": "string", // Format: YYYY-MM-DDTHH:MM:SS
        "expires_at": "string",  // Format: YYYY-MM-DDTHH:MM:SS
        "status": "string",     // e.g., "Selling", "Listing", "Approved"
        "created_at": "string"  // Format: YYYY-MM-DDTHH:MM:SS
      }
    ]
    ```
  - **404 Not Found**:

    ```json
    {
      "error": "User not found"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "Unauthorized access"
    }
    ```

### Add Item

**Add a new food item (batch) to inventory.**

- **Method**: POST
- **URL**: `/retailers/add_item`
- **Authentication**: Retailer Required
- **Content-Type**: `application/json`
- **Request Body**:

  ```json
  {
    "name": "string",
    "quantity": "integer",
    "best_before": "string", // Format: YYYY-MM-DDTHH:MM:SS
    "expires_at": "string"   // Format: YYYY-MM-DDTHH:MM:SS
  }
  ```
- **Responses**:
  - **201 Created**:

    ```json
    {
      "id": integer,
      "name": "string",
      "quantity": integer,
      "best_before": "string", // Format: YYYY-MM-DDTHH:MM:SS
      "expires_at": "string",  // Format: YYYY-MM-DDTHH:MM:SS
      "status": "string"      // e.g., "Selling"
    }
    ```
  - **422 Unprocessable Entity**:

    ```json
    {
      "error": "Missing required fields"
    }
    ```
  - **400 Bad Request**:

    ```json
    {
      "error": "Invalid quantity" or "Invalid date range"
    }
    ```
  - **404 Not Found**:

    ```json
    {
      "error": "User not found"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "Unauthorized access"
    }
    ```

### Remove Item

**Remove an inventory item (batch).**

- **Method**: DELETE
- **URL**: `/retailers/item/remove/<int:item_id>`
  - `<int:item_id>`: ID of the inventory item
- **Authentication**: Retailer Required
- **Responses**:
  - **200 OK**:

    ```json
    {
      "message": "Item removed successfully"
    }
    ```
  - **404 Not Found**:

    ```json
    {
      "error": "Inventory item not found"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "User not found or not a retailer"
    }
    ```
  - **400 Bad Request**:

    ```json
    {
      "error": "<error>"
    }
    ```

### Sell Inventory Item

**Sell quantity from an inventory item.**

- **Method**: POST
- **URL**: `/retailers/inventory/<int:id>/sell`
  - `<int:id>`: ID of the inventory item
- **Authentication**: Retailer Required
- **Content-Type**: `application/json`
- **Request Body**:

  ```json
  {
    "quantity": "integer"
  }
  ```
- **Responses**:
  - **200 OK**:

    ```json
    {
      "message": "Sold <quantity> of <name>",
      "remaining_quantity": integer
    }
    ```
  - **422 Unprocessable Entity**:

    ```json
    {
      "error": "Quantity is required"
    }
    ```
  - **400 Bad Request**:

    ```json
    {
      "error": "Cannot sell after expiry date" or "Insufficient quantity"
    }
    ```
  - **404 Not Found**:

    ```json
    {
      "error": "Inventory item not found"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "Unauthorized access"
    }
    ```

### List Inventory Item

**Change item status to 'Listing'.**

- **Method**: POST
- **URL**: `/retailers/inventory/<int:id>/list`
  - `<int:id>`: ID of the inventory item
- **Authentication**: Retailer Required
- **Responses**:
  - **200 OK**:

    ```json
    {
      "message": "Food listed for NGOs"
    }
    ```
  - **404 Not Found**:

    ```json
    {
      "error": "Inventory item not found or no quantity available"
    }
    ```
  - **422 Unprocessable Entity**:

    ```json
    {
      "error": "Cannot list before expiry date"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "Unauthorized access"
    }
    ```

### Get Notifications

**Get notifications for the authenticated retailer.**

- **Method**: GET
- **URL**: `/retailers/notifications`
- **Authentication**: Retailer Required
- **Responses**:
  - **200 OK**:

    ```json
    [
      {
        "id": integer,
        "message": "string",
        "options": ["List", "Ignore"],
        "food_id": integer
      }
    ]
    ```
  - **404 Not Found**:

    ```json
    {
      "error": "User not found"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "Unauthorized access"
    }
    ```

### Get Requests

**Get requests from NGOs for the retailer's food.**

- **Method**: GET
- **URL**: `/retailers/requests`
- **Authentication**: Retailer Required
- **Query Parameters**:
  - `pincode` (optional, string): Filter by pincode
- **Responses**:
  - **200 OK**:

    ```json
    [
      {
        "id": integer,
        "food_id": integer,
        "ngo_id": integer,
        "quantity": integer,
        "status": "string", // e.g., "pending", "approved", "ignored"
        "pickup_date": "string", // Format: YYYY-MM-DDTHH:MM:SS or null
        "created_at": "string"   // Format: YYYY-MM-DDTHH:MM:SS
      }
    ]
    ```
  - **404 Not Found**:

    ```json
    {
      "error": "User not found"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "Unauthorized access"
    }
    ```

### Approve Request

**Approve an NGO's request for a food item.**

- **Method**: POST
- **URL**: `/retailers/requests/<int:request_id>/approve`
  - `<int:request_id>`: ID of the food request
- **Authentication**: Retailer Required
- **Responses**:
  - **200 OK**:

    ```json
    {
      "message": "Request approved"
    }
    ```
  - **404 Not Found**:

    ```json
    {
      "error": "Request not found or already processed"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "User not found or not a retailer"
    }
    ```

### Ignore Request

**Ignore an NGO's request for a food item.**

- **Method**: POST
- **URL**: `/retailers/requests/<int:request_id>/ignore`
  - `<int:request_id>`: ID of the food request
- **Authentication**: Retailer Required
- **Responses**:
  - **200 OK**:

    ```json
    {
      "message": "Request ignored"
    }
    ```
  - **404 Not Found**:

    ```json
    {
      "error": "Request not found or already processed"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "User not found or not a retailer"
    }
    ```

### Ignore Notification

**Ignore notification for an item.**

- **Method**: POST
- **URL**: `/retailers/food/<int:id>/ignore`
  - `<int:id>`: ID of the inventory item
- **Authentication**: Retailer Required
- **Responses**:
  - **200 OK**:

    ```json
    {
      "message": "Notification ignored"
    }
    ```
  - **404 Not Found**:

    ```json
    {
      "error": "Item not found or not eligible for ignore"
    }
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "User not found or not a retailer"
    }
    ```

---

## Admin Routes

### Get All Food

**Get all food items (for admin/debug purposes).**

- **Method**: GET
- **URL**: `/admin/food`
- **Authentication**: Admin Required
- **Responses**:
  - **200 OK**:

    ```json
    [
      {
        "id": integer,
        "name": "string",
        "quantity": integer,
        "best_before": "string", // Format: YYYY-MM-DDTHH:MM:SS
        "expires_at": "string",  // Format: YYYY-MM-DDTHH:MM:SS
        "status": "string",     // e.g., "Selling", "Listing", "Approved"
        "created_at": "string", // Format: YYYY-MM-DDTHH:MM:SS
        "owner_id": integer     // ID of the owning user
      }
    ]
    ```
  - **403 Forbidden**:

    ```json
    {
      "error": "User not found or not an admin"
    }
    ```

---

## Notes for Frontend Team

- **JWT Token**: Store the `token` from the `/login` response and include it in the `Authorization` header for protected routes (e.g., `Bearer <token>`).
- **Error Handling**: Check for `error` fields in responses to display user-friendly messages (e.g., for 400, 401, 403, or 404 errors).
- **Role-Based Access**:
  - Retailers: Use `/retailers/*` endpoints.
  - NGOs: Use `/ngo/*` endpoints.
  - Admins: Use `/admin/*` endpoints.
- **Date Formats**: Use `YYYY-MM-DDTHH:MM:SS` for `best_before`, `expires_at`, `pickup_date`, and `created_at`.
- **Background Notifications**: The backend runs a daily check to send notifications for items past "best before" but before "expires at." Frontend should poll `/retailers/notifications` or use WebSocket for real-time updates.
- **CORS**: Supports cross-origin requests (`origins=["*"]`), requiring no additional frontend configuration.

---

## Example Workflow

1. **User Registration**:
   - Send a POST to `/sign-up` with user details and role (e.g., "Retailer").
   - Receive `{"message": "User created successfully"}`.

2. **User Login**:
   - Send a POST to `/login` with `{"email": "user@example.com", "password": "pass"}`.
   - Receive a token valid for 1 day.

3. **Retailer Adds Food**:
   - Send a POST to `/retailers/add_item` with food details.
   - Receive the created item details.

4. **Retailer Sells Food**:
   - Send a POST to `/retailers/inventory/<id>/sell` with `{"quantity": 50}`.
   - Receive `{"message": "Sold 50 of <name>"}`.

5. **Retailer Lists Food**:
   - After "best before," send a POST to `/retailers/inventory/<id>/list`.
   - Receive `{"message": "Food listed for NGOs"}`.

6. **NGO Requests Food**:
   - Get listed food via `/ngo/filtered_food`, then send a POST to `/ngo/request/<id>` with `{"quantity": 20}`.
   - Receive a request ID.

7. **Retailer Approves Request**:
   - View requests via `/retailers/requests`, then send a POST to `/retailers/requests/<request_id>/approve`.
   - Receive `{"message": "Request approved"}`.

8. **NGO Claims Food**:
   - Send a POST to `/ngo/claim/<request_id>`.
   - Receive `{"message": "Food claimed successfully"}`.

9. **Admin Debug**:
   - Send a GET to `/admin/food` to view all food items.
   - Receive a detailed list.

---