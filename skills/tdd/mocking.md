# When to Mock

Mock at **system boundaries** only:

- External APIs (payment, email, third-party HTTP)
- AWS and other cloud SDKs
- Databases (sometimes - prefer a real one in a container)
- Time/randomness
- File system (sometimes - prefer `t.TempDir()` / `tmp_path`)

Don't mock:

- Your own types/modules
- Internal collaborators
- Anything you control

## Prefer real things over mocks

Reach for these before writing a fake:

- **HTTP servers**: `httptest.NewServer` (Go), `respx` / `responses` / `pytest-httpserver` (Python). Real HTTP, canned responses, no mock objects.
- **Databases, queues, caches**: `testcontainers-go` / `testcontainers-python` with the same engine and version as production. Gate them behind a build tag (`//go:build integration`) or a pytest marker if they're slow, and say which one the slice needs.
- **AWS**: `moto` (Python) or LocalStack; for Go, a small consumer-side interface over the client you use (below). Never point tests at a real account, and never read real credentials in tests.
- **Kubernetes**: `client-go`'s `fake.NewSimpleClientset()` for controller logic; `envtest` when behavior depends on the API server (admission, defaulting).

## Designing for Mockability

At system boundaries, design interfaces that are easy to mock:

**1. Use dependency injection**

Pass external dependencies in rather than creating them internally:

```go
// Easy to mock
func ProcessPayment(ctx context.Context, o Order, c PaymentClient) error {
	return c.Charge(ctx, o.Total)
}

// Hard to mock
func ProcessPayment(ctx context.Context, o Order) error {
	c := stripe.NewClient(os.Getenv("STRIPE_KEY"))
	return c.Charge(ctx, o.Total)
}
```

```python
# Easy to mock
def process_payment(order: Order, client: PaymentClient) -> Receipt:
    return client.charge(order.total)

# Hard to mock
def process_payment(order: Order) -> Receipt:
    client = StripeClient(os.environ["STRIPE_KEY"])
    return client.charge(order.total)
```

The same goes for time: take a `func() time.Time` / `clock` parameter (or a `Clock` interface) instead of calling `time.Now()` / `datetime.now()` inside the logic.

**2. Define small interfaces where they're consumed (Go)**

Don't mock the whole AWS SDK client. Declare the one or two methods your package actually calls, in your package, and let the real client satisfy it:

```go
// in package uploader, not in a shared "interfaces" package
type objectPutter interface {
	PutObject(ctx context.Context, in *s3.PutObjectInput, opts ...func(*s3.Options)) (*s3.PutObjectOutput, error)
}
```

A hand-written fake of a two-method interface beats a generated mock: no call-count assertions, just behavior. In Python, a `typing.Protocol` plays the same role.

**3. Prefer SDK-style interfaces over generic fetchers**

Create specific functions for each external operation instead of one generic function with conditional logic:

```python
# GOOD: Each method is independently fakeable
class UsersAPI(Protocol):
    def get_user(self, user_id: str) -> User: ...
    def get_orders(self, user_id: str) -> list[Order]: ...
    def create_order(self, data: NewOrder) -> Order: ...

# BAD: Faking requires conditional logic inside the fake
class API(Protocol):
    def request(self, method: str, path: str, body: dict | None = None) -> dict: ...
```

The SDK approach means:
- Each fake returns one specific shape
- No conditional logic in test setup
- Easier to see which endpoints a test exercises
- Type safety per endpoint
