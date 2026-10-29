# Good and Bad Tests

## Good Tests

**Integration-style**: Test through real interfaces, not mocks of internal parts.

```go
// GOOD: Tests observable behavior, from the external test package
package orders_test

func TestCheckout_ConfirmsValidCart(t *testing.T) {
	cart := orders.NewCart()
	cart.Add(product)

	got, err := orders.Checkout(context.Background(), cart, payment)
	if err != nil {
		t.Fatalf("Checkout: %v", err)
	}
	if got.Status != orders.StatusConfirmed {
		t.Errorf("Status = %q, want %q", got.Status, orders.StatusConfirmed)
	}
}
```

```python
# GOOD: Tests observable behavior
def test_checkout_confirms_valid_cart() -> None:
    cart = Cart()
    cart.add(product)
    result = checkout(cart, payment_method)
    assert result.status == Status.CONFIRMED
```

Characteristics:

- Tests behavior users/callers care about
- Uses public API only (exported Go identifiers, non-underscore Python names)
- Survives internal refactors
- Describes WHAT, not HOW
- One logical assertion per test (or per table row)

## Bad Tests

**Implementation-detail tests**: Coupled to internal structure.

```python
# BAD: Tests implementation details
def test_checkout_calls_payment_service(mocker) -> None:
    process = mocker.patch("shop.orders._payment_service.process")
    checkout(cart, payment)
    process.assert_called_once_with(cart.total)
```

Red flags:

- Mocking internal collaborators (`mocker.patch` on your own module, a hand-rolled fake of a type you own)
- Testing unexported functions from an internal `package orders` test, or `_private` helpers
- Asserting on call counts/order (`assert_called_once_with`, gomock `.Times(1)`, `InOrder`)
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT
- Verifying through external means instead of interface

```go
// BAD: Bypasses interface to verify
func TestCreateUser_SavesToDatabase(t *testing.T) {
	_, _ = svc.CreateUser(ctx, users.New{Name: "Alice"})
	var n int
	db.QueryRow(`SELECT count(*) FROM users WHERE name = $1`, "Alice").Scan(&n)
	if n != 1 {
		t.Fatal("not saved")
	}
}

// GOOD: Verifies through interface
func TestCreateUser_MakesUserRetrievable(t *testing.T) {
	u, err := svc.CreateUser(ctx, users.New{Name: "Alice"})
	if err != nil {
		t.Fatalf("CreateUser: %v", err)
	}
	got, err := svc.GetUser(ctx, u.ID)
	if err != nil {
		t.Fatalf("GetUser: %v", err)
	}
	if got.Name != "Alice" {
		t.Errorf("Name = %q, want %q", got.Name, "Alice")
	}
}
```

**Tautological tests**: Expected value restates the implementation, so the test passes by construction.

```python
# BAD: Expected value is recomputed the way the code computes it
def test_calculate_total_sums_line_items() -> None:
    items = [Item(price=10), Item(price=5)]
    expected = sum(i.price for i in items)
    assert calculate_total(items) == expected

# GOOD: Expected value is an independent, known literal
def test_calculate_total_sums_line_items() -> None:
    assert calculate_total([Item(price=10), Item(price=5)]) == 15
```

Golden files are the Go-flavoured trap: regenerating them with `-update` and committing without reading the diff makes every golden test tautological. Review each golden diff as if it were a hand-written expectation.

## Table-driven tests

Idiomatic in Go (`t.Run` over a slice of cases) and in pytest (`@pytest.mark.parametrize`). In TDD they grow **one row per cycle**: add the row, see it fail, make it pass. A table written in full before any implementation is horizontal slicing.

```go
tests := []struct {
	name string
	in   string
	want time.Duration
}{
	{"seconds", "30s", 30 * time.Second}, // cycle 1
	{"minutes", "5m", 5 * time.Minute},   // cycle 2
	// next cycle adds the next row, not before
}
```

Use `t.Parallel()` only when the cases share no state, and name rows by behavior so `-run 'TestParse/minutes'` reads like a spec.
