# CBC Resources API Documentation

## Overview
This API provides endpoints for managing educational resources, user accounts, orders, payments, and website content.

## Base URL
```
https://api.example.com/
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
            "downloads_remaining": 2,
            "expires_at": "2024-01-01T00:00:00Z",
            "last_downloaded": "2023-12-01T10:30:00Z",
            "download_history": [
                {
                    "downloaded_at": "2023-12-01T10:30:00Z",
                    "device_type": "Desktop",
                    "os_type": "Windows 10",
                    "browser_type": "Chrome 120.0.0",
                    "status": "success",
                    "download_duration": 5.2
                }
            ]
        }
    ]
}
```

### Download File
```http
GET /api/downloads/{token}

Headers:
Authorization: Bearer <access_token>

Success Response:
File download starts with appropriate Content-Type and Content-Disposition headers

Error Responses:
{
    "error": "Download link has expired or exceeded limit"
    "status": 410
}

{
    "error": "File not found"
    "status": 404
}

{
    "error": "Invalid download link"
    "status": 404
}

Notes:
- Downloads are limited to 5 attempts per purchase
- Download links expire after 30 days
- All download attempts are logged with device information
- File downloads are tracked for analytics and security
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
- page: Page number (default: 1)
- page_size: Items per page (default: 20, max: 100)
- status: Filter by status (approved, pending, rejected)
- min_price: Minimum price filter
- max_price: Maximum price filter

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
            "preview_url": "https://example.com/previews/math.pdf",
            "file_type": "PDF",
            "file_size": "25MB",
            "download_count": 150,
            "rating": 4.5,
            "review_count": 25,
            "category": {
                "id": "uuid",
                "name": "Mathematics",
                "slug": "mathematics",
                "icon": "calculator",
                "parent": null
            },
            "subject": {
                "id": "uuid",
                "name": "Mathematics",
                "code": "MAT",
                "description": "Mathematics subject"
            },
            "grade": "4",
            "created_at": "2023-12-01T10:30:00Z",
            "updated_at": "2023-12-02T15:45:00Z",
            "meta": {
                "title": "Grade 4 Mathematics - CBC Resources",
                "description": "Complete mathematics course for Grade 4",
                "keywords": "mathematics, grade 4, cbc"
            }
        }
    ]
}
```

### Get Product Details
```http
GET /products/{slug}/

Response:
{
    "id": "uuid",
    "name": "Grade 4 Mathematics",
    "slug": "grade-4-mathematics",
    "description": "Complete mathematics course with detailed explanations",
    "price": 1500,
    "thumbnail_url": "https://example.com/thumbnails/math.jpg",
    "preview_url": "https://example.com/previews/math.pdf",
    "file_type": "PDF",
    "file_size": "25MB",
    "download_count": 150,
    "rating": 4.5,
    "review_count": 25,
    "category": {
        "id": "uuid",
        "name": "Mathematics",
        "slug": "mathematics",
        "icon": "calculator",
        "parent": null,
        "children": [
            {
                "id": "uuid",
                "name": "Algebra",
                "slug": "algebra",
                "icon": "function"
            }
        ]
    },
    "subject": {
        "id": "uuid",
        "name": "Mathematics",
        "code": "MAT",
        "description": "Mathematics subject"
    },
    "grade": "4",
    "created_at": "2023-12-01T10:30:00Z",
    "updated_at": "2023-12-02T15:45:00Z",
    "meta": {
        "title": "Grade 4 Mathematics - CBC Resources",
        "description": "Complete mathematics course for Grade 4",
        "keywords": "mathematics, grade 4, cbc"
    },
    "related_products": [
        {
            "id": "uuid",
            "name": "Grade 4 Mathematics Workbook",
            "slug": "grade-4-mathematics-workbook",
            "thumbnail_url": "https://example.com/thumbnails/workbook.jpg",
            "price": 1000
        }
    ]
}
```

### List Categories
```http
GET /products/categories/

Query Parameters:
- parent: Filter by parent category ID (optional)
- active: Filter by active status (true/false)

Response:
{
    "count": 50,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "name": "Mathematics",
            "slug": "mathematics",
            "description": "Mathematics resources",
            "icon": "calculator",
            "image_url": "https://example.com/categories/math.jpg",
            "parent": null,
            "children": [
                {
                    "id": "uuid",
                    "name": "Algebra",
                    "slug": "algebra",
                    "icon": "function"
                }
            ],
            "product_count": 25,
            "active": true,
            "order": 1,
            "meta": {
                "title": "Mathematics Resources - CBC",
                "description": "Mathematics learning resources",
                "keywords": "mathematics, learning, cbc"
            }
        }
    ]
}
```

### List Subjects
```http
GET /products/subjects/

Query Parameters:
- active: Filter by active status (true/false)

Response:
{
    "count": 10,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "name": "Mathematics",
            "code": "MAT",
            "description": "Mathematics subject",
            "active": true,
            "product_count": 25
        }
    ]
}
```

## Orders

### Create Order
```http
POST /api/orders/

Headers:
Authorization: Bearer <access_token>

Request:
{
    "items": [
        {
            "product_id": "uuid",
            "quantity": 1
        }
    ],
    "customer_email": "user@example.com",
    "customer_phone": "+254700000000",
    "notes": "Special instructions"
}

Response:
{
    "id": "uuid",
    "order_number": "ORD-2023-001",
    "status": "pending",
    "subtotal": 1500,
    "tax_amount": 0,
    "total_amount": 1500,
    "created_at": "2023-12-01T10:30:00Z",
    "items": [
        {
            "id": "uuid",
            "product": {
                "id": "uuid",
                "name": "Grade 4 Mathematics",
                "thumbnail_url": "https://example.com/thumbnails/math.jpg"
            },
            "quantity": 1,
            "unit_price": 1500,
            "total": 1500
        }
    ],
    "payment_url": "https://example.com/pay/order-id"
}
```

### Quick Checkout
```http
POST /api/orders/quick-checkout

Headers:
Authorization: Bearer <access_token>

Request:
{
    "product_id": "uuid",
    "quantity": 1,
    "customer_email": "user@example.com",
    "customer_phone": "+254700000000"
}

Response:
{
    "success": true,
    "order": {
        "id": "uuid",
        "order_number": "ORD-2023-001",
        "status": "pending",
        "total_amount": 1500,
        "items": [...]
    },
    "checkout_url": "/api/orders/uuid/checkout"
}
```

### List Orders
```http
GET /api/orders

Headers:
Authorization: Bearer <access_token>

Query Parameters:
- page: Page number (default: 1)
- page_size: Items per page (default: 20, max: 100)
- status: Filter by status (pending, paid, failed, cancelled, refunded)
- ordering: Sort field (created_at, -created_at, total_amount, -total_amount)

Response:
{
    "count": 25,
    "next": "http://api.example.com/api/orders/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "order_number": "ORD-2023-001",
            "status": "paid",
            "total_amount": 1500,
            "created_at": "2023-12-01T10:30:00Z",
            "payment_method": "mpesa",
            "payment_status": "completed",
            "items_count": 2,
            "download_available": true
        }
    ]
}
```

### Get Order Details
```http
GET /api/orders/{order_id}

Headers:
Authorization: Bearer <access_token>

Response:
{
    "id": "uuid",
    "order_number": "ORD-2023-001",
    "status": "paid",
    "subtotal": 1500,
    "tax_amount": 0,
    "total_amount": 1500,
    "created_at": "2023-12-01T10:30:00Z",
    "payment_method": "mpesa",
    "payment_reference": "MPESA123456",
    "payment_date": "2023-12-01T10:35:00Z",
    "customer_email": "user@example.com",
    "customer_phone": "+254700000000",
    "items": [
        {
            "id": "uuid",
            "product": {
                "id": "uuid",
                "name": "Grade 4 Mathematics",
                "thumbnail_url": "https://example.com/thumbnails/math.jpg"
            },
            "quantity": 1,
            "unit_price": 1500,
            "total": 1500,
            "download_url": "https://example.com/downloads/token/xyz",
            "download_count": 2,
            "download_limit": 5,
            "download_expires_at": "2024-01-01T00:00:00Z"
        }
    ],
    "payments": [
        {
            "id": "uuid",
            "amount": 1500,
            "payment_method": "mpesa",
            "status": "completed",
            "created_at": "2023-12-01T10:32:00Z",
            "processed_at": "2023-12-01T10:35:00Z"
        }
    ]
}
```

### Cancel Order
```http
POST /api/orders/{order_id}/cancel

Headers:
Authorization: Bearer <access_token>

Response:
{
    "success": true,
    "message": "Order ORD-2023-001 has been cancelled"
}

Error Response:
{
    "error": "Order cannot be cancelled",
    "status": 400
}
```

### Process Free Order
```http
POST /api/orders/{order_id}/process-free

Headers:
Authorization: Bearer <access_token>

Response:
{
    "success": true,
    "message": "Order processed successfully",
    "order": {
        "id": "uuid",
        "order_number": "ORD-2023-001",
        "status": "paid",
        "items": [
            {
                "product_name": "Free Resource",
                "download_url": "https://example.com/downloads/token/xyz"
            }
        ]
    }
}

Error Response:
{
    "error": "This order requires payment",
    "status": 400
}
```

## Payments

### Initiate Payment
```http
POST /api/payments/initiate/

Headers:
Authorization: Bearer <access_token>

Request:
{
    "order_id": "uuid",
    "payment_method": "mpesa",
    "phone_number": "+254700000000"
}

Response:
{
    "success": true,
    "message": "Payment request sent. Please check your phone and enter M-Pesa PIN.",
    "payment_id": "uuid",
    "checkout_request_id": "ws_CO_123456789",
    "order": {
        "id": "uuid",
        "order_number": "ORD-2023-001",
        "total_amount": 1500
    }
}

Error Response:
{
    "error": "Payment initiation failed",
    "details": "Invalid phone number format",
    "status": 400
}
```

### Check Payment Status
```http
GET /api/payments/{payment_id}/status/

Headers:
Authorization: Bearer <access_token>

Response:
{
    "status": "completed",
    "order_status": "paid",
    "message": "Payment successful",
    "order_id": "uuid",
    "download_items": [
        {
            "product_title": "Grade 4 Mathematics",
            "download_url": "https://example.com/downloads/token/xyz"
        }
    ]
}

Possible Status Values:
- pending: Initial payment state
- processing: Payment is being processed (e.g., waiting for M-Pesa)
- completed: Payment successful
- failed: Payment failed
- cancelled: Payment was cancelled
- refunded: Payment has been refunded

Error Response:
{
    "error": "Payment not found",
    "status": 404
}
```

### Get Checkout Details
```http
GET /api/orders/{order_id}/checkout

Headers:
Authorization: Bearer <access_token>

Response:
{
    "order": {
        "id": "uuid",
        "order_number": "ORD-2023-001",
        "status": "pending",
        "total_amount": 1500,
        "items": [...]
    },
    "payment_methods": [
        {
            "value": "mpesa",
            "label": "M-Pesa"
        },
        {
            "value": "card",
            "label": "Credit/Debit Card"
        }
    ],
    "is_free": false
}

Error Response:
{
    "error": "Order not found",
    "status": 404
}
```

### List Payment History
```http
GET /api/payments/history/

Headers:
Authorization: Bearer <access_token>

Query Parameters:
- page: Page number (default: 1)
- page_size: Items per page (default: 20, max: 100)
- status: Filter by status (completed, failed, pending, refunded)
- payment_method: Filter by payment method (mpesa, card)
- start_date: Filter by date range start (YYYY-MM-DD)
- end_date: Filter by date range end (YYYY-MM-DD)

Response:
{
    "count": 25,
    "next": "http://api.example.com/api/payments/history/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "order_number": "ORD-2023-001",
            "amount": 1500,
            "payment_method": "mpesa",
            "status": "completed",
            "created_at": "2023-12-01T10:30:00Z",
            "processed_at": "2023-12-01T10:35:00Z",
            "payment_reference": "MPESA123456",
            "failure_reason": null
        }
    ]
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
    "address": "123 Education Street, Nairobi",
    "working_hours": "Monday - Friday, 8:00 AM - 5:00 PM",
    "social_links": {
        "facebook": "https://facebook.com/cbcresources",
        "twitter": "https://twitter.com/cbcresources",
        "instagram": "https://instagram.com/cbcresources",
        "linkedin": "https://linkedin.com/company/cbcresources"
    },
    "meta": {
        "title": "CBC Resources - Quality Educational Materials",
        "description": "Access high-quality CBC educational resources",
        "keywords": "cbc, education, resources, kenya"
    }
}
```

### Contact Form
```http
POST /website/api/contact/

Request:
{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+254700000000",
    "subject": "Product Inquiry",
    "message": "I need more information about...",
    "priority": "normal"
}

Response:
{
    "success": true,
    "message": "Thank you for contacting us. We will respond shortly.",
    "reference_number": "INQ-2023-001"
}

Error Response:
{
    "error": "Invalid form data",
    "details": {
        "email": ["Enter a valid email address"]
    },
    "status": 400
}
```

### FAQs
```http
GET /website/api/faqs/

Query Parameters:
- category: Filter by category (optional)
- search: Search in questions/answers (optional)

Response:
{
    "count": 20,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "question": "How do I download my purchased resources?",
            "answer": "After successful payment, go to your dashboard...",
            "category": "Downloads",
            "order": 1
        }
    ]
}
```

### Terms of Service
```http
GET /website/api/terms/

Response:
{
    "content": "<h1>Terms of Service</h1>...",
    "last_updated": "2023-12-01T10:30:00Z",
    "version": "1.0"
}
```

### Privacy Policy
```http
GET /website/api/privacy/

Response:
{
    "content": "<h1>Privacy Policy</h1>...",
    "last_updated": "2023-12-01T10:30:00Z",
    "version": "1.0",
    "data_retention": {
        "account_data": "2 years after account deletion",
        "order_data": "7 years",
        "download_logs": "1 year"
    }
}
```

### Testimonials
```http
GET /website/api/testimonials/

Query Parameters:
- page: Page number (default: 1)
- page_size: Items per page (default: 10, max: 50)

Response:
{
    "count": 50,
    "next": "http://api.example.com/website/api/testimonials/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "name": "Jane Doe",
            "role": "Teacher",
            "school": "ABC Primary School",
            "content": "The resources have greatly improved our teaching...",
            "rating": 5,
            "avatar_url": "https://example.com/avatars/jane.jpg",
            "created_at": "2023-12-01T10:30:00Z",
            "verified": true
        }
    ]
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