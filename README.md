# CBC Resources API Documentation

## Overview
This API provides endpoints for managing educational resources, user accounts, orders, payments, and website content.

## Base URL
```
http://api.example.com/
```

## Authentication
The API uses JWT (JSON Web Token) authentication. Include the token in the Authorization header:
```
Authorization: Bearer <access_token>
```

### Authentication Endpoints

#### Obtain Token
```http
POST /accounts/api/token/

Request:
{
    "email": "user@example.com",
    "password": "your_password"
}

Response:
{
    "access": "access_token_here",
    "refresh": "refresh_token_here"
}
```

#### Refresh Token
```http
POST /accounts/api/token/refresh/

Request:
{
    "refresh": "refresh_token_here"
}

Response:
{
    "access": "new_access_token_here"
}
```

## User Management

### Registration
```http
POST /accounts/api/register/

Request:
{
    "email": "user@example.com",
    "username": "username",
    "password": "StrongPassword123!",
    "password_confirm": "StrongPassword123!"
}

Response:
{
    "success": true,
    "message": "Registration successful! Welcome email has been sent.",
    "user": {
        "id": "uuid",
        "email": "user@example.com",
        "username": "username"
    },
    "tokens": {
        "refresh": "refresh_token",
        "access": "access_token"
    }
}
```

### Profile Management
```http
GET /accounts/api/profile/
PUT /accounts/api/profile/

Request (PUT):
{
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+254700000000",
    "bio": "About me",
    "avatar": "file_upload"
}

Response:
{
    "id": "uuid",
    "email": "user@example.com",
    "username": "username",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+254700000000",
    "bio": "About me",
    "avatar_url": "https://example.com/avatars/user.jpg"
}
```

## User Dashboard

### Dashboard Summary
```http
GET /accounts/api/dashboard/

Response:
{
    "total_orders": 15,
    "completed_orders": 12,
    "pending_orders": 3,
    "total_spent": 25000,
    "recent_orders": [
        {
            "order_number": "ORD-2023-001",
            "total_amount": 2500,
            "status": "paid",
            "created_at": "2023-12-01T10:30:00Z"
        }
    ],
    "recent_downloads": [
        {
            "product_name": "Grade 4 Mathematics",
            "downloaded_at": "2023-12-02T15:45:00Z"
        }
    ]
}
```

### User Downloads
```http
GET /accounts/api/downloads/

Response:
{
    "count": 25,
    "next": "http://api.example.com/accounts/api/downloads/?page=2",
    "previous": null,
    "results": [
        {
            "product_name": "Grade 5 Science",
            "thumbnail_url": "https://example.com/thumbnails/science.jpg",
            "download_url": "https://example.com/downloads/token/xyz",
            "order_number": "ORD-2023-001",
            "file_type": "PDF",
            "file_size": "25MB",
            "download_count": 3,
            "last_downloaded": "2023-12-01T10:30:00Z"
        }
    ]
}
```

## Products

### List Products
```http
GET /products/

Query Parameters:
- category: Filter by category slug
- subject: Filter by subject ID
- grade: Filter by grade level
- search: Search term
- ordering: Sort field (price, -price, created_at, -created_at)
- page: Page number
- page_size: Items per page

Response:
{
    "count": 100,
    "next": "http://api.example.com/products/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "name": "Grade 4 Mathematics",
            "slug": "grade-4-mathematics",
            "description": "Complete mathematics course",
            "price": 1500,
            "thumbnail_url": "https://example.com/thumbnails/math.jpg",
            "category": {
                "name": "Mathematics",
                "slug": "mathematics"
            },
            "subject": {
                "name": "Mathematics",
                "code": "MAT"
            },
            "grade": "4"
        }
    ]
}
```

## Orders

### Create Order
```http
POST /orders/create/

Request:
{
    "items": [
        {
            "product_id": "uuid",
            "quantity": 1
        }
    ]
}

Response:
{
    "id": "uuid",
    "order_number": "ORD-2023-001",
    "status": "pending",
    "total_amount": 1500,
    "items": [
        {
            "product_name": "Grade 4 Mathematics",
            "quantity": 1,
            "price": 1500
        }
    ],
    "payment_url": "https://example.com/pay/order-id"
}
```

## Payments

### Initiate Payment
```http
POST /payments/initiate/

Request:
{
    "order_id": "uuid",
    "payment_method": "mpesa",
    "phone_number": "+254700000000"
}

Response:
{
    "payment_id": "uuid",
    "checkout_url": "https://example.com/checkout/payment-id",
    "status": "pending"
}
```

### Check Payment Status
```http
GET /payments/{payment_id}/status/

Response:
{
    "status": "completed",
    "message": "Payment successful",
    "download_url": "https://example.com/download/token"
}
```

## Website Content

### Website Information
```http
GET /website/api/website-info/

Response:
{
    "name": "CBC Resources",
    "description": "Educational resources platform",
    "contact_email": "contact@example.com",
    "contact_phone": "+254700000000",
    "social_links": {
        "facebook": "https://facebook.com/cbcresources",
        "twitter": "https://twitter.com/cbcresources"
    }
}
```

## Error Responses

The API uses standard HTTP status codes and returns error messages in a consistent format:

```json
{
    "success": false,
    "message": "Error description",
    "errors": {
        "field_name": [
            "Error detail"
        ]
    }
}
```

Common status codes:
- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Internal Server Error

## Rate Limiting

API requests are limited to:
- 100 requests per minute for authenticated users
- 20 requests per minute for unauthenticated users

## Pagination

List endpoints return paginated results with the following structure:
```json
{
    "count": 100,
    "next": "http://api.example.com/endpoint/?page=2",
    "previous": null,
    "results": []
}
```

Default page size is 20 items. Maximum page size is 100 items.