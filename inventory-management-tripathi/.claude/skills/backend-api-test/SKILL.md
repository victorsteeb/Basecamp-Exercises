---
name: backend-api-test
description: Guidelines for writing backend API tests using pytest and FastAPI TestClient. Use this skill when writing or modifying tests in tests/backend directory.
---

# Backend API Testing Guidelines

This skill provides comprehensive guidelines for writing backend API tests for the Factory Inventory Management System. Follow these patterns to ensure consistent, thorough test coverage.

## Directory Structure

All backend tests must be placed in `tests/backend/`:

```
tests/backend/
├── conftest.py           # Shared fixtures and test client setup
├── test_inventory.py     # Inventory endpoint tests
├── test_orders.py        # Orders endpoint tests
├── test_dashboard.py     # Dashboard endpoint tests
└── test_misc_endpoints.py # Other endpoint tests
```

## File Organization

### 1. File Naming
- Use `test_<feature>.py` format (e.g., `test_inventory.py`, `test_orders.py`)
- Group related endpoints in the same file
- Create new files for distinct API feature areas

### 2. Test Class Structure
Organize tests within a class using descriptive names:

```python
"""
Tests for <feature> API endpoints.
"""
import pytest


class Test<Feature>Endpoints:
    """Test suite for <feature>-related endpoints."""

    def test_get_all_<resources>(self, client):
        """Test getting all <resources>."""
        # Test implementation
```

## Core Testing Patterns

### 1. Basic Endpoint Tests

**Always test the happy path first:**

```python
def test_get_all_orders(self, client):
    """Test getting all orders."""
    response = client.get("/api/orders")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Verify structure of first item
    first_order = data[0]
    assert "id" in first_order
    assert "order_number" in first_order
    # ... other required fields
```

### 2. Filter Testing

Test each query parameter filter individually and in combination:

```python
def test_get_orders_by_warehouse(self, client):
    """Test filtering orders by warehouse."""
    response = client.get("/api/orders?warehouse=Tokyo")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    # Verify all results match the filter
    for order in data:
        assert order["warehouse"] == "Tokyo"

def test_get_orders_multiple_filters(self, client):
    """Test filtering orders with multiple filters."""
    response = client.get(
        "/api/orders?warehouse=San Francisco&category=Power Supplies&status=Delivered"
    )
    assert response.status_code == 200

    data = response.json()

    # Verify all results match ALL filters
    for order in data:
        assert order["warehouse"] == "San Francisco"
        assert order["category"].lower() == "power supplies"
        assert order["status"].lower() == "delivered"
```

**Common filters to test:**
- `warehouse` - Filter by warehouse location
- `category` - Filter by product category
- `status` - Filter by order status (orders only)
- `month` - Filter by month in format `YYYY-MM` or quarter `Q1-2025`

### 3. Single Resource Tests

Test fetching individual resources by ID:

```python
def test_get_order_by_id(self, client):
    """Test getting a specific order by ID."""
    # First get all orders to find a valid ID
    response = client.get("/api/orders")
    all_orders = response.json()
    assert len(all_orders) > 0

    first_order_id = all_orders[0]["id"]

    # Now get that specific order
    response = client.get(f"/api/orders/{first_order_id}")
    assert response.status_code == 200

    order = response.json()
    assert order["id"] == first_order_id

def test_get_nonexistent_order(self, client):
    """Test getting an order that doesn't exist."""
    response = client.get("/api/orders/nonexistent-order-999")
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()
```

### 4. Data Structure Validation

Verify the response structure matches the API contract:

```python
def test_order_items_structure(self, client):
    """Test that order items have proper structure."""
    response = client.get("/api/orders")
    data = response.json()

    for order in data:
        assert "items" in order
        assert isinstance(order["items"], list)

        for item in order["items"]:
            assert "sku" in item
            assert "name" in item
            assert "quantity" in item
            assert "unit_price" in item
            assert isinstance(item["quantity"], int)
            assert isinstance(item["unit_price"], (int, float))
```

### 5. Data Type Validation

Ensure numeric fields have correct types and valid ranges:

```python
def test_inventory_quantity_types(self, client):
    """Test that quantity fields are proper numeric types."""
    response = client.get("/api/inventory")
    data = response.json()

    for item in data:
        assert isinstance(item["quantity_on_hand"], int)
        assert isinstance(item["reorder_point"], int)
        assert isinstance(item["unit_cost"], (int, float))
        assert item["quantity_on_hand"] >= 0
        assert item["reorder_point"] >= 0
        assert item["unit_cost"] >= 0
```

### 6. Business Logic Validation

Test calculated values and business rules:

```python
def test_order_total_value_calculation(self, client):
    """Test that order total values are reasonable."""
    response = client.get("/api/orders")
    data = response.json()

    for order in data:
        assert "total_value" in order
        assert isinstance(order["total_value"], (int, float))
        assert order["total_value"] > 0

        # Verify total makes sense based on items
        calculated_total = sum(
            item["quantity"] * item["unit_price"]
            for item in order["items"]
        )
        # Allow small floating point differences
        assert abs(order["total_value"] - calculated_total) < 0.01
```

### 7. Enum/Status Value Validation

Verify constrained fields have valid values:

```python
def test_order_status_values(self, client):
    """Test that orders have valid status values."""
    response = client.get("/api/orders")
    data = response.json()

    valid_statuses = ["delivered", "shipped", "processing", "backordered"]

    for order in data:
        assert order["status"].lower() in valid_statuses
```

### 8. Date Format Validation

Verify date fields are properly formatted:

```python
def test_order_dates_format(self, client):
    """Test that order dates are in proper format."""
    response = client.get("/api/orders")
    data = response.json()

    for order in data:
        assert "order_date" in order
        assert "expected_delivery" in order
        # Date should contain year, month pattern (ISO format)
        assert "2025-" in order["order_date"]
        assert "-" in order["expected_delivery"]
        assert "T" in order["expected_delivery"]  # Has time component
```

### 9. Cross-Endpoint Validation

Test that aggregated endpoints match raw data:

```python
def test_dashboard_pending_orders_calculation(self, client):
    """Test that pending orders are calculated correctly."""
    # Get all orders
    orders_response = client.get("/api/orders")
    all_orders = orders_response.json()

    # Count processing and backordered orders
    pending_count = sum(
        1 for order in all_orders
        if order["status"].lower() in ["processing", "backordered"]
    )

    # Get dashboard summary
    dashboard_response = client.get("/api/dashboard/summary")
    dashboard_data = dashboard_response.json()

    assert dashboard_data["pending_orders"] == pending_count
```

## Using Fixtures

### Available Fixtures (from conftest.py)

1. **`client`** - FastAPI TestClient instance (required for all tests)
2. **`sample_inventory_item`** - Example inventory item structure
3. **`sample_order`** - Example order structure

### Using the Client Fixture

```python
def test_example(self, client):
    """Every test method needs the client fixture."""
    response = client.get("/api/endpoint")
    assert response.status_code == 200
```

### Creating New Fixtures

Add shared fixtures to [conftest.py](tests/backend/conftest.py):

```python
@pytest.fixture
def sample_warehouse_data():
    """Sample warehouse data for testing."""
    return {
        "name": "San Francisco",
        "location": "CA",
        # ... other fields
    }
```

## Test Naming Conventions

Use descriptive names that clearly indicate what is being tested:

- `test_get_all_<resources>` - Get all items without filters
- `test_get_<resource>_by_<filter>` - Single filter tests
- `test_get_<resource>_multiple_filters` - Combined filter tests
- `test_get_<resource>_by_id` - Single item retrieval
- `test_get_nonexistent_<resource>` - 404 handling
- `test_<resource>_<field>_structure` - Data structure validation
- `test_<resource>_<field>_types` - Data type validation
- `test_<resource>_<calculation>_calculation` - Business logic

## Common Assertions

### Status Codes
```python
assert response.status_code == 200  # Success
assert response.status_code == 404  # Not found
assert response.status_code == 422  # Validation error
```

### Response Types
```python
data = response.json()
assert isinstance(data, list)    # Array response
assert isinstance(data, dict)    # Object response
assert len(data) > 0             # Has data
```

### Field Presence
```python
assert "field_name" in data
assert "detail" in error_response  # Error messages
```

### String Comparisons (Case-Insensitive)
```python
assert order["status"].lower() == "delivered"
assert item["category"].lower() == "power supplies"
```

### Floating Point Comparisons
```python
# Allow small differences for float calculations
assert abs(calculated - expected) < 0.01
```

## API Endpoint Reference

### Inventory Endpoints
- `GET /api/inventory` - All inventory items
  - Filters: `warehouse`, `category`
- `GET /api/inventory/{id}` - Single inventory item

### Orders Endpoints
- `GET /api/orders` - All orders
  - Filters: `warehouse`, `category`, `status`, `month`
- `GET /api/orders/{id}` - Single order

### Dashboard Endpoints
- `GET /api/dashboard/summary` - Dashboard summary
  - Filters: `warehouse`, `category`, `status`, `month`

### Other Endpoints
- `GET /api/demand` - Demand forecast (no filters)
- `GET /api/backlog` - Backlog items (no filters)
- `GET /api/spending/*` - Spending data endpoints

## Common Values for Testing

### Warehouses
- San Francisco
- London
- Tokyo

### Categories
- Circuit Boards
- Sensors
- Power Supplies
- Connectors
- Mechanical Components

### Order Statuses
- Delivered
- Shipped
- Processing
- Backordered

### Date Formats
- Single month: `2025-01`, `2025-02`, etc.
- Quarter: `Q1-2025`, `Q2-2025`, etc.
- All: `all`

## Best Practices

1. **Test one thing per test** - Each test should verify a single behavior
2. **Use descriptive assertions** - Clear error messages help debugging
3. **Test edge cases** - Empty results, nonexistent IDs, invalid filters
4. **Verify data integrity** - Check types, ranges, and calculated values
5. **Test filters independently** - Then test combinations
6. **Use case-insensitive comparisons** - For string fields like status/category
7. **Allow floating point tolerance** - Use `abs(a - b) < 0.01` for money calculations
8. **Test error responses** - Verify proper 404 handling
9. **Validate complete structure** - Check all required fields are present
10. **Cross-validate endpoints** - Dashboard should match raw data

## Running Tests

```bash
# Run all backend tests
pytest tests/backend/

# Run specific test file
pytest tests/backend/test_orders.py

# Run specific test class
pytest tests/backend/test_orders.py::TestOrdersEndpoints

# Run specific test method
pytest tests/backend/test_orders.py::TestOrdersEndpoints::test_get_all_orders

# Run with verbose output
pytest tests/backend/ -v

# Run with coverage
pytest tests/backend/ --cov=server
```

## Example: Complete Test File Template

```python
"""
Tests for <feature> API endpoints.
"""
import pytest


class Test<Feature>Endpoints:
    """Test suite for <feature>-related endpoints."""

    def test_get_all_<resources>(self, client):
        """Test getting all <resources>."""
        response = client.get("/api/<resources>")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Verify structure
        first_item = data[0]
        assert "id" in first_item
        # Add other required fields

    def test_get_<resource>_by_filter(self, client):
        """Test filtering <resources> by <filter>."""
        response = client.get("/api/<resources>?<filter>=<value>")
        assert response.status_code == 200

        data = response.json()

        # Verify filter applied correctly
        for item in data:
            assert item["<filter>"] == "<value>"

    def test_get_<resource>_by_id(self, client):
        """Test getting a specific <resource> by ID."""
        # Get valid ID first
        response = client.get("/api/<resources>")
        all_items = response.json()
        item_id = all_items[0]["id"]

        # Get specific item
        response = client.get(f"/api/<resources>/{item_id}")
        assert response.status_code == 200

        item = response.json()
        assert item["id"] == item_id

    def test_get_nonexistent_<resource>(self, client):
        """Test getting a <resource> that doesn't exist."""
        response = client.get("/api/<resources>/nonexistent-999")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
```

## Key Reminders

- **Always use the `client` fixture** - It's the TestClient for making API calls
- **Test filters thoroughly** - Individual filters and combinations
- **Validate response structure** - Check all required fields exist
- **Use lowercase for string comparisons** - Categories and statuses vary in case
- **Test both success and error paths** - 200 and 404 responses
- **Verify data types** - Use `isinstance()` for proper type checking
- **Test business logic** - Calculations, aggregations, and derived values
- **Keep tests independent** - Each test should work in isolation
