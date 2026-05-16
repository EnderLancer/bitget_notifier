from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class Order(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order_id: str = Field(alias="orderId")
    client_oid: str | None = Field(default=None, alias="clientOid")
    symbol: str
    side: str
    order_type: str = Field(alias="orderType")
    size: Decimal
    price: Decimal = Decimal("0")
    status: str
    leverage: str | None = None
    margin_mode: str | None = Field(default=None, alias="marginMode")
    updated_at: int = Field(default=0, alias="uTime")

    def fingerprint(self) -> tuple[str, Decimal, Decimal]:
        """Fields whose change should trigger a MODIFIED event."""
        return (self.status, self.size, self.price)
