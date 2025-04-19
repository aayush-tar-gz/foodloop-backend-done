Okay, here is the API documentation for the routes you've provided, including the authentication routes, retailer routes, and NGO routes.

I will format this like a typical API documentation, followed by a summary table.

**Base URL:** `http://127.0.0.1:3000` (adjust if your app runs on a different host/port)

**Authentication:**
Most API endpoints require authentication using a JSON Web Token (JWT). Obtain a token by logging in via the `/auth-login` endpoint and include it in the `Authorization` header of subsequent requests in the format `Bearer YOUR_JWT_TOKEN_HERE`.

---

### **Authentication Routes**

**1. Sign Up**

* **URL:** `/sign-up`
* **Method:** `POST`
* **Description:** Registers a new user with a specific role.
* **Authentication:** None required.
* **Request Body:** `application/json`
    ```json
    {
      "email": "user@example.com",
      "password": "securepassword123",
      "city": "Some City",
      "pincode": "123456",
      "contact": "9876543210",
      "role": "Retailer"  // or "Ngo", "Farmer", "Admin"
    }
    ```
    * `email`: User's email (must be unique).
    * `password`: User's password.
    * `city`: User's city.
    * `pincode`: User's pincode.
    * `contact`: User's contact number.
    * `role`: The desired role for the user (case-insensitive, but stored capitalized). Must be one of the valid roles defined in the backend.
* **Success Response:** `201 Created`
    ```json
    {
      "message": "User created successfully"
    }
    ```
* **Error Responses:**
    * `402`: Missing required fields in the request body.
        ```json
        {"error": "Missing required fields"}
        ```
    * `409`: Email address already registered.
        ```json
        {"error": "Email address is already registered"}
        ```
    * `403`: Invalid role provided.
        ```json
        {"error": "Invalid role: InvalidRoleName"}
        ```
    * `400`: Role name not found in the database.
        ```json
        {"error": "Role 'NonExistentRole' not found"}
        ```
    * `500`: Internal server error during registration (e.g., database issue).
        ```json
        {"error": "An error occurred during registration: <error details>"}
        ```

**2. Login**

* **URL:** `/auth-login`
* **Method:** `POST`
* **Description:** Authenticates a user and returns a JWT access token.
* **Authentication:** None required.
* **Request Body:** `application/json`
    ```json
    {
      "email": "user@example.com",
      "password": "securepassword123"
    }
    ```
    * `email`: User's email.
    * `password`: User's password.
* **Success Response:** `200 OK`
    ```json
    {
      "message": "Login successful",
      "token": "eyJhbGciOi...", // Your JWT access token
      "user": {
        "id": 1,
        "email": "user@example.com",
        "city": "Some City",
        "pincode": "123456",
        "contact": "9876543210",
        "roles": ["Retailer"] // List of user's roles
      }
    }
    ```
* **Error Responses:**
    * `402`: Missing email or password in the request body.
        ```json
        {"error": "Email and password are required"}
        ```
    * `401`: Invalid email or password.
        ```json
        {"error": "Invalid email or password"}
        ```

**3. Logout**

* **URL:** `/logout`
* **Method:** `POST`
* **Description:** Logs out the user. (Note: As this API primarily uses stateless JWTs, this endpoint clears the server-side session but doesn't invalidate the JWT itself until it expires. Its main use might be for session-based contexts).
* **Authentication:** None required (based on provided code, but unusual for a JWT API).
* **Request Body:** None.
* **Success Response:** `200 OK`
    ```json
    {
      "message": "Logged out successfully"
    }
    ```

---

### **Retailer Routes**

*(All routes under `/retailers` require a valid JWT in the `Authorization: Bearer <token>` header.)*

**1. Get Retailer Inventory**

* **URL:** `/retailers/inventory`
* **Method:** `GET`
* **Description:** Retrieves the authenticated retailer's inventory items.
* **Authentication:** JWT Required.
* **URL Parameters:** None.
* **Request Body:** None.
* **Success Response:** `200 OK`
    ```json
    [
      {
        "id": 1,         // InventoryItem ID
        "food_id": 101,  // Linked Food ID
        "name": "Apples",
        "quantity": 150.0,
        "best_before": "2025-04-26T12:00:00", // ISO 8601 format or null
        "expires_at": "2025-05-10T12:00:00",   // ISO 8601 format or null
        "status": "Selling", // or "Listing", "Approved", etc.
        "created_at": "2025-04-19T18:00:00"    // ISO 8601 format or null
      },
      // ... more inventory items
    ]
    ```
* **Error Responses:**
    * `401`: Missing or invalid JWT.
    * `404`: User not found (unlikely if authenticated via JWT).

**2. Add/Update Inventory Item**

* **URL:** `/retailers/add_item`
* **Method:** `POST`
* **Description:** Adds a new type of food to the retailer's inventory or adds quantity to an existing item.
* **Authentication:** JWT Required.
* **URL Parameters:** None.
* **Request Body:** `application/json`
    ```json
    {
      "name": "Bananas",
      "quantity": 50.0
    }
    ```
    * `name`: Name of the food item.
    * `quantity`: Quantity to add (must be > 0).
* **Success Responses:**
    * `201 Created` (If adding a new food type globally, or if adding an existing type for the first time for this retailer)
        ```json
        {
          "id": 5,         // New InventoryItem ID
          "food_id": 105,  // New or Existing Food ID
          "name": "Bananas",
          "quantity": 50.0, // Note: quantity in response might reflect global stock if Food.quantity is global
          "best_before": "2025-05-01T12:00:00",
          "expires_at": "2025-05-15T12:00:00",
          "status": "Selling"
        }
        ```
    * `200 OK` (If adding quantity to an item the retailer already stocks)
        ```json
        {
          "id": 1,         // Existing InventoryItem ID
          "food_id": 101,  // Existing Food ID
          "name": "Apples",
          "quantity": 200.0, // Updated global quantity
          "best_before": "2025-04-26T12:00:00",
          "expires_at": "2025-05-10T12:00:00",
          "status": "Selling",
          "message": "Added 50.0 to existing 'Apples'. Total quantity: 200.0"
        }
        ```
* **Error Responses:**
    * `401`: Missing or invalid JWT.
    * `404`: User not found (unlikely).
    * `422`: Missing required fields, invalid quantity format/value, invalid date format from date service, or generated dates are invalid (e.g., don't meet minimum future requirements).
        ```json
        {"error": "Missing required fields (name or quantity)"}
        {"error": "Invalid quantity format"}
        {"error": "Quantity must be greater than 0"}
        {"error": "Failed to get valid dates for new item 'Bananas'. Invalid format from date service."}
        {"error": "Generated dates are invalid (best before must be at least 7 days from today, and expiry at least 14 days after best before)"}
        ```
    * `409`: Conflict - Attempted to create a new food type name that already exists globally.
        ```json
        {"error": "Food item type with name 'Apples' already exists in the system and could not be added as a new type. (Constraint Error)"}
        {"error": "Internal error: Attempted to create duplicate food type name 'Apples'."} // Less likely with correct logic
        ```
    * `500`: Unexpected error (e.g., Gemini API failure, database error not specifically caught).
        ```json
        {"error": "An unexpected error occurred: <error details>"}
        {"error": "Database error: <db error details>"}
        ```

**3. Get Retailer's Incoming Food Requests**

* **URL:** `/retailers/requested_food`
* **Method:** `GET`
* **Description:** Retrieves food requests made by NGOs for this retailer's inventory items.
* **Authentication:** JWT Required.
* **URL Parameters:** None.
* **Request Body:** None.
* **Success Response:** `200 OK`
    ```json
    [
      {
        "id": 201,     // FoodRequest ID
        "food_id": 101, // Linked Food ID
        "ngo_id": 501,  // ID of the requesting NGO user
        "quantity": 30.0, // Quantity requested by the NGO
        "status": "pending", // or "approved", "ignored"
        "pickup_date": "2025-04-21T10:00:00", // ISO 8601 format or null
        "created_at": "2025-04-20T00:30:00"   // ISO 8601 format
      },
      // ... more requests
    ]
    ```
* **Error Responses:**
    * `401`: Missing or invalid JWT.
    * `404`: User not found (unlikely).

**4. Sell Inventory Item**

* **URL:** `/retailers/inventory/<int:id>/sell`
* **Method:** `POST`
* **Description:** Records the sale of a quantity of an inventory item. Deducts quantity from stock.
* **Authentication:** JWT Required.
* **URL Parameters:**
    * `id` (integer): The ID of the InventoryItem to sell from.
* **Request Body:** `application/json`
    ```json
    {
      "quantity": 10.5
    }
    ```
    * `quantity`: The quantity to sell (must be > 0).
* **Success Response:** `200 OK`
    ```json
    {
      "message": "Sold 10.5 of Apples",
      "remaining_quantity": 140.5
    }
    ```
* **Error Responses:**
    * `401`: Missing or invalid JWT.
    * `404`: Inventory item not found or does not belong to the authenticated retailer.
    * `415`: Request body is not JSON.
    * `422`: Quantity is missing, invalid format, <= 0, or insufficient quantity in stock.
        ```json
        {"error": "Quantity is required"}
        {"error": "Invalid quantity value format"}
        {"error": "Quantity must be greater than 0"}
        {"error": "Insufficient quantity"}
        ```
    * `422`: Cannot sell after the item's expiry date.
        ```json
        {"error": "Cannot sell after expiry date"}
        ```
    * `500`: Database error or unexpected server error.
        ```json
        {"error": "Database error occurred while selling item"}
        {"error": "An unexpected error occurred: <error details>"}
        ```

**5. List Inventory Item for NGOs**

* **URL:** `/retailers/inventory/<int:id>/list`
* **Method:** `POST`
* **Description:** Marks an inventory item as "Listing", making it visible to NGOs (assuming it meets other criteria like quantity and location).
* **Authentication:** JWT Required.
* **URL Parameters:**
    * `id` (integer): The ID of the InventoryItem to list.
* **Request Body:** None.
* **Success Response:** `200 OK`
    ```json
    {
      "message": "Food listed for NGOs"
    }
    ```
* **Error Responses:**
    * `401`: Missing or invalid JWT.
    * `404`: Inventory item not found or does not belong to the authenticated retailer, or has zero quantity.
    * `422`: Cannot list the item based on its dates. (Note: Current code enforces 'Cannot list before expiry date', which may need review based on intended logic).
        ```json
        {"error": "Cannot list before expiry date"}
        ```
    * `500`: Database error or unexpected server error.
        ```json
        {"error": "Database error occurred while listing item"}
        {"error": "An unexpected error occurred: <error details>"}
        ```

**6. Get Notifications**

* **URL:** `/retailers/notifications`
* **Method:** `GET`
* **Description:** Retrieves notifications for the retailer (currently based on items past their best before date with status "Selling").
* **Authentication:** JWT Required.
* **URL Parameters:** None.
* **Request Body:** None.
* **Success Response:** `200 OK`
    ```json
    [
      {
        "id": 1,        // InventoryItem ID
        "message": "Your Apples (remaining: 140.5) is past best before. List it or ignore.",
        "options": ["List", "Ignore"]
      },
      // ... more notifications
    ]
    ```
* **Error Responses:**
    * `401`: Missing or invalid JWT.
    * `404`: User not found (unlikely).

**7. Approve Food Request**

* **URL:** `/retailers/requests/<int:request_id>/approve`
* **Method:** `POST`
* **Description:** Approves a pending food request made by an NGO. Changes request status to "approved" and the linked Food item status to "Approved".
* **Authentication:** JWT Required.
* **URL Parameters:**
    * `request_id` (integer): The ID of the FoodRequest to approve.
* **Request Body:** None.
* **Success Response:** `200 OK`
    ```json
    {
      "message": "Request approved"
    }
    ```
* **Error Responses:**
    * `401`: Missing or invalid JWT.
    * `404`: Request not found, does not belong to the authenticated retailer's inventory item, or is not in "pending" status.
        ```json
        {"error": "Request not found or already processed"}
        ```

**8. Ignore Food Request**

* **URL:** `/retailers/requests/<int:request_id>/ignore`
* **Method:** `POST`
* **Description:** Ignores (declines) a pending food request made by an NGO. Changes request status to "ignored".
* **Authentication:** JWT Required.
* **URL Parameters:**
    * `request_id` (integer): The ID of the FoodRequest to ignore.
* **Request Body:** None.
* **Success Response:** `200 OK`
    ```json
    {
      "message": "Request ignored"
    }
    ```
* **Error Responses:**
    * `401`: Missing or invalid JWT.
    * `404`: Request not found, does not belong to the authenticated retailer's inventory item, or is not in "pending" status.
        ```json
        {"error": "Request not found or already processed"}
        ```

**9. Remove Inventory Item**

* **URL:** `/retailers/item/remove/<int:item_id>`
* **Method:** `DELETE`
* **Description:** Removes an inventory item entry for the retailer. (Note: This deletes the InventoryItem link, but the linked Food item remains in the database due to schema).
* **Authentication:** JWT Required + User must have the "Retailer" role.
* **URL Parameters:**
    * `item_id` (integer): The ID of the InventoryItem to remove.
* **Request Body:** None.
* **Success Response:** `200 OK`
    ```json
    {
      "message": "Item removed successfully"
    }
    ```
* **Error Responses:**
    * `401`: Missing or invalid JWT.
    * `404`: User not found, does not have the "Retailer" role, or the inventory item is not found or does not belong to the authenticated retailer.
        ```json
        {"error": "User not found or not a retailer"}
        {"error": "Inventory item not found"}
        ```
    * `400`: General error during deletion (e.g., database issue).
        ```json
        {"error": "<error details>"}
        ```

**10. Ignore Notification**

* **URL:** `/retailers/food/<int:id>/ignore`
* **Method:** `POST`
* **Description:** Acknowledges or ignores a specific notification related to an inventory item. (Note: Based on code, this doesn't change item status, just returns success).
* **Authentication:** JWT Required + User must have the "Retailer" role.
* **URL Parameters:**
    * `id` (integer): The ID of the InventoryItem associated with the notification.
* **Request Body:** None.
* **Success Response:** `200 OK`
    ```json
    {
      "message": "Notification ignored"
    }
    ```
* **Error Responses:**
    * `401`: Missing or invalid JWT.
    * `404`: User not found, does not have the "Retailer" role, or the item is not found/not retailer's/not in "Selling" or "Listing" status.
        ```json
        {"error": "User not found or not a retailer"}
        {"error": "Item not found or not eligible for ignore"}
        ```

---

### **NGO Routes**

*(All routes under `/ngo` require a valid JWT in the `Authorization: Bearer <token>` header.)*

**1. Get Filtered (Nearby & Listed) Food**

* **URL:** `/ngo/filtered_food`
* **Method:** `GET`
* **Description:** Retrieves food items listed by retailers in the same pincode as the authenticated NGO, which are currently in "Listing" status and have quantity > 0.
* **Authentication:** JWT Required.
* **URL Parameters:** None.
* **Request Body:** None.
* **Success Response:** `200 OK`
    ```json
    [
      {
        "id": 1,         // InventoryItem ID
        "name": "Bananas",
        "quantity": 50.0,
        "best_before": "2025-05-01T12:00:00", // ISO 8601 format
        "expires_at": "2025-05-15T12:00:00",   // ISO 8601 format
        "location": {
          "city": "Indore",
          "pincode": "452001"
        },
        "retailer_contact": "1112223330"
      },
      // ... more listed items in the same pincode
    ]
    ```
* **Error Responses:**
    * `401`: Missing or invalid JWT.
    * `404`: User not found (unlikely).

**2. Create Food Request**

* **URL:** `/ngo/request`
* **Method:** `POST`
* **Description:** Creates a new food request for a specific listed inventory item.
* **Authentication:** JWT Required.
* **URL Parameters:** None.
* **Request Body:** `application/json`
    ```json
    {
      "inventory_item_id": 1,       // The ID of the InventoryItem the NGO wants to request
      "quantity": 30.0,             // The quantity the NGO is requesting
      "pickup_date": "2025-04-21T10:00:00", // Optional: Desired pickup date/time (ISO 8601)
      "notes": "Urgent need for distribution tomorrow." // Optional: Notes for the retailer
    }
    ```
    * `inventory_item_id`: The ID of the InventoryItem being requested (required).
    * `quantity`: The quantity being requested (must be > 0) (required).
    * `pickup_date`: Desired pickup date/time (optional, ISO 8601 string).
    * `notes`: Any notes for the retailer (optional string).
* **Success Response:** `201 Created`
    ```json
    {
      "id": 202, // The ID of the newly created FoodRequest
      "message": "Food request created successfully"
      // Optional: Includes details like inventory_item_id, quantity, pickup_date etc. if returned by endpoint
    }
    ```
* **Error Responses:**
    * `401`: Missing or invalid JWT.
    * `404`: User not found (unlikely).
    * `400`: Bad request data (e.g., missing required fields like `inventory_item_id` or `quantity`, non-numeric quantity, quantity <= 0, database error).
        ```json
        {"error": "Missing required fields (inventory_item_id or quantity)"}
        {"error": "Requested quantity must be greater than 0"}
        {"error": "Failed to create food request. Please check your input. Details: <db error or type error>"}
        ```
    * `422`: Invalid format for optional fields, like `pickup_date`.
        ```json
        {"error": "Invalid pickup_date format. Use YYYY-MM-DDTHH:MM:SS"}
        ```
    * `500`: Unexpected internal server error.
        ```json
        {"error": "An unexpected internal error occurred: <error details>"}
        ```

**3. Get NGO's Own Requests**

* **URL:** `/ngo/my_requests`
* **Method:** `GET`
* **Description:** Retrieves all food requests made by the authenticated NGO.
* **Authentication:** JWT Required.
* **URL Parameters:** None.
* **Request Body:** None.
* **Success Response:** `200 OK`
    ```json
    [
      {
        "id": 201,     // FoodRequest ID
        "inventory_item": { // Details of the requested item
          "id": 1,      // InventoryItem ID
          "name": "Apples",
          "quantity": 150.0 // Quantity of the item in the retailer's inventory (may not be the requested quantity)
        },
        "status": "pending", // or "approved", "ignored"
        "created_at": "2025-04-20T00:30:00"   // ISO 8601 format
      },
      // ... more requests made by this NGO
    ]
    ```
* **Error Responses:**
    * `401`: Missing or invalid JWT.
    * `404`: User not found (unlikely).

---

### **Route Summary Table**

| Method   | Path                                               | Description                                                                | Authentication          |
| :------- | :------------------------------------------------- | :------------------------------------------------------------------------- | :---------------------- |
| `POST`   | `/sign-up`                                         | Register a new user with a role.                                           | None                    |
| `POST`   | `/auth-login`                                      | Authenticate user and return JWT token.                                    | None                    |
| `POST`   | `/logout`                                          | Log out user (clears session, limited JWT relevance).                      | None Required           |
| `GET`    | `/retailers/inventory`                             | Get authenticated retailer's inventory items.                              | JWT Required            |
| `POST`   | `/retailers/add_item`                              | Add new inventory item or add quantity to existing item.                   | JWT Required            |
| `GET`    | `/retailers/requested_food`                        | Get food requests made by NGOs for this retailer.                          | JWT Required            |
| `POST`   | `/retailers/inventory/<int:id>/sell`               | Sell quantity from an inventory item.                                      | JWT Required            |
| `POST`   | `/retailers/inventory/<int:id>/list`               | Mark an inventory item as "Listing".                                       | JWT Required            |
| `GET`    | `/retailers/notifications`                         | Get retailer notifications (expiry, etc.).                                 | JWT Required            |
| `POST`   | `/retailers/requests/<int:request_id>/approve`     | Approve a pending food request.                                            | JWT Required            |
| `POST`   | `/retailers/requests/<int:request_id>/ignore`      | Ignore (decline) a pending food request.                                   | JWT Required            |
| `DELETE` | `/retailers/item/remove/<int:item_id>`             | Remove an inventory item.                                                  | JWT Required + Retailer |
| `POST`   | `/retailers/food/<int:id>/ignore`                  | Acknowledge/ignore an item notification.                                   | JWT Required + Retailer |
| `GET`    | `/ngo/filtered_food`                               | Get food items listed by nearby retailers with "Listing" status.           | JWT Required            |
| `POST`   | `/ngo/request`                                     | Create a food request for a listed inventory item.                         | JWT Required            |
| `GET`    | `/ngo/my_requests`                                 | Get authenticated NGO's own food requests.                                 | JWT Required            |

---

This documentation covers the endpoints, methods, descriptions, authentication requirements, and the expected structure of requests and responses based on the code you provided.
