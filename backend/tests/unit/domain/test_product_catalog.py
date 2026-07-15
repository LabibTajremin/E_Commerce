from decimal import Decimal
from uuid import uuid4

import pytest

from src.domain.entities.product import Product, ProductStatus
from src.domain.exceptions import ValidationError
from src.domain.value_objects.money import Money
from src.domain.value_objects.sku import SKU
from src.domain.value_objects.slug import Slug


def _product(**overrides: object) -> Product:
    defaults: dict[str, object] = {
        "tenant_id": uuid4(),
        "name": "Widget",
        "slug": Slug("widget"),
        "price": Money(Decimal("9.99")),
    }
    defaults.update(overrides)
    return Product(**defaults)  # type: ignore[arg-type]


def test_negative_price_rejected() -> None:
    with pytest.raises(ValueError):
        Money(Decimal("-1.00"))


def test_negative_stock_qty_rejected() -> None:
    with pytest.raises(ValidationError):
        _product(stock_qty=-1)


def test_compare_at_price_below_price_rejected() -> None:
    with pytest.raises(ValidationError):
        _product(price=Money(Decimal("10.00")), compare_at_price=Money(Decimal("5.00")))


def test_new_product_defaults_to_draft() -> None:
    product = _product()
    assert product.status == ProductStatus.DRAFT


def test_publish_and_unpublish() -> None:
    product = _product()
    product.publish()
    assert product.status == ProductStatus.PUBLISHED
    product.unpublish()
    assert product.status == ProductStatus.DRAFT


def test_adjust_stock_increases_and_decreases() -> None:
    product = _product(stock_qty=5)
    product.adjust_stock(3)
    assert product.stock_qty == 8
    product.adjust_stock(-8)
    assert product.stock_qty == 0


def test_adjust_stock_rejects_oversell() -> None:
    product = _product(stock_qty=2)
    with pytest.raises(ValidationError):
        product.adjust_stock(-3)


def test_reorder_images_requires_same_set() -> None:
    product = _product(images=["a", "b", "c"])
    product.reorder_images(["c", "a", "b"])
    assert product.images == ["c", "a", "b"]

    with pytest.raises(ValidationError):
        product.reorder_images(["a", "b"])


@pytest.mark.parametrize("invalid", ["", "ab_cd", "-abc", "abc-", "UPPER"])
def test_invalid_slug_rejected(invalid: str) -> None:
    with pytest.raises(ValueError):
        Slug(invalid)


def test_slug_from_text_normalizes() -> None:
    assert str(Slug.from_text("Cool Widget!! 2000")) == "cool-widget-2000"


@pytest.mark.parametrize("invalid", ["", "a b", "$$$", "-ABC", "ABC-"])
def test_invalid_sku_rejected(invalid: str) -> None:
    with pytest.raises(ValueError):
        SKU(invalid)


def test_sku_normalizes_to_uppercase() -> None:
    assert str(SKU("wid-001")) == "WID-001"
