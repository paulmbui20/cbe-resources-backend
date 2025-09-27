# Accounts API Documentation

## Authentication Endpoints

### Token Authentication

- `POST /accounts/api/token/` - Obtain JWT token pair
- `POST /accounts/api/token/refresh/` - Refresh JWT token
- `POST /accounts/api/token/verify/` - Verify JWT token

### Registration and Profile

- `POST /accounts/api/register/` - Register a new user
- `GET /accounts/api/profile/` - Get user profile
- `PUT/PATCH /accounts/api/profile/` - Update user profile
- `POST /accounts/api/change-password/` - Change user password

### Email Verification

- `POST /accounts/api/send-verification/` - Send verification email
- `GET /accounts/api/verify-email/<uidb64>/<token>/` - Verify email with token
- `POST /accounts/api/resend-verification/` - Resend verification email
- `GET /accounts/api/verification-status/` - Check verification status

### Availability Checks

- `POST /accounts/api/check-username/` - Check username availability
- `POST /accounts/api/check-email/` - Check email availability

## User Dashboard Endpoints

### Dashboard Summary

- `GET /accounts/api/dashboard/` - Get user dashboard summary
  - Returns overview of user activity including counts and recent items
  - Includes total orders, purchases, downloads, and recent activity

### Downloads

- `GET /accounts/api/downloads/` - List user's downloads
  - Returns all downloadable items purchased by the user
  - Includes download URLs, file information, and download counts
  - Supports pagination

### Purchases

- `GET /accounts/api/purchases/` - List user's purchases
  - Returns all products purchased by the user
  - Includes product information, purchase date, and download status
  - Supports pagination

### Orders

- `GET /accounts/api/orders/` - List user's orders
  - Returns all orders placed by the user
  - Includes order status, total amount, and item count
  - Supports pagination

### Payments

- `GET /accounts/api/payments/` - List user's payment history
  - Returns all payment transactions made by the user
  - Includes payment method, status, and amount
  - Supports pagination

### Statistics

- `GET /accounts/api/stats/` - Get user statistics
  - Returns aggregated statistics about user activity
  - Includes total spent, download counts, and purchase metrics

### Download History

- `GET /accounts/api/download-history/` - Get user's download history
  - Returns detailed information about download activity
  - Includes timestamps and download counts

## Authentication

All dashboard endpoints require authentication with a valid JWT token. Include the token in the Authorization header:

```
Authorization: Bearer <token>
```

## Response Format

All API responses are returned in JSON format. Paginated endpoints include:

```json
{
  "count": 100,           // Total number of items
  "next": "URL",         // URL to next page (null if no next page)
  "previous": "URL",     // URL to previous page (null if no previous page)
  "results": []          // Array of items for current page
}
```

## Error Handling

Errors are returned with appropriate HTTP status codes and a JSON response with error details:

```json
{
  "error": "Error message",
  "details": {}           // Optional detailed error information
}
```

Common error status codes:
- 400: Bad Request - Invalid input
- 401: Unauthorized - Authentication required
- 403: Forbidden - Insufficient permissions
- 404: Not Found - Resource not found
- 500: Internal Server Error - Server-side error