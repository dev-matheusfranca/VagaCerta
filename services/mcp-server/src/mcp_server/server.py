from datetime import date, datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

INSTRUCTIONS = (
    "Ferramentas para agendar horários em barbearias, salões, clínicas e espaços de bem-estar. "
    "Os horários são sempre no fuso do estabelecimento. Antes de agendar, entrar na lista de "
    "espera ou cancelar, confirme os dados com a pessoa."
)


def checked(response: httpx.Response) -> Any:
    # Erros esperados voltam para o modelo como mensagem, para ele explicar ou tentar de novo.
    if response.status_code in (404, 409, 422):
        raise ToolError(str(response.json()["detail"]))
    response.raise_for_status()
    return response.json()


def brl(cents: int) -> str:
    return f"R$ {cents / 100:.2f}".replace(".", ",")


def create_server(
    catalog: httpx.AsyncClient,
    booking: httpx.AsyncClient,
    waitlist: httpx.AsyncClient,
    web_url: str,
) -> MCPServer:
    mcp = MCPServer("VagaCerta", instructions=INSTRUCTIONS)

    @mcp.tool()
    async def list_businesses() -> list[dict[str, str]]:
        """Lista os estabelecimentos com id, nome, categoria e endereço."""
        businesses = checked(await catalog.get("/businesses"))
        return [{key: b[key] for key in ("id", "name", "category", "address")} for b in businesses]

    @mcp.tool()
    async def get_business(business_id: UUID) -> dict[str, Any]:
        """Mostra os profissionais e os serviços (duração e preço) de um estabelecimento."""
        business = checked(await catalog.get(f"/businesses/{business_id}"))
        return {
            "id": business["id"],
            "name": business["name"],
            "address": business["address"],
            "professionals": [
                {"id": p["id"], "name": p["name"], "specialty": p["specialty"]}
                for p in business["professionals"]
            ],
            "services": [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "duration_minutes": s["duration_minutes"],
                    "price": brl(s["price_cents"]),
                }
                for s in business["services"]
            ],
        }

    @mcp.tool()
    async def find_slots(
        business_id: UUID, professional_id: UUID, service_id: UUID, day: date
    ) -> dict[str, Any]:
        """Horários livres de um profissional para um serviço num dia (AAAA-MM-DD)."""
        timezone = checked(await catalog.get(f"/businesses/{business_id}"))["timezone"]
        availability = checked(
            await booking.get(
                "/availability",
                params={
                    "business_id": str(business_id),
                    "professional_id": str(professional_id),
                    "service_id": str(service_id),
                    "date": str(day),
                },
            )
        )
        slots = [
            datetime.fromisoformat(s).astimezone(ZoneInfo(timezone)) for s in availability["slots"]
        ]
        return {
            "day": str(day),
            "slots": [{"time": s.strftime("%H:%M"), "starts_at": s.isoformat()} for s in slots],
        }

    @mcp.tool()
    async def book_appointment(
        business_id: UUID,
        professional_id: UUID,
        service_id: UUID,
        starts_at: datetime,
        customer_name: str,
        customer_email: str,
    ) -> dict[str, str]:
        """Agenda um horário. Use um `starts_at` devolvido por find_slots."""
        booked = checked(
            await booking.post(
                "/bookings",
                json={
                    "business_id": str(business_id),
                    "professional_id": str(professional_id),
                    "service_id": str(service_id),
                    "starts_at": starts_at.isoformat(),
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                },
            )
        )
        return {
            "booking_id": booked["id"],
            "status": booked["status"],
            "link": f"{web_url}/agendamentos/{booked['id']}",
        }

    @mcp.tool()
    async def join_waitlist(
        business_id: UUID,
        professional_id: UUID,
        service_id: UUID,
        day: date,
        customer_name: str,
        customer_email: str,
    ) -> dict[str, int]:
        """Põe a pessoa na fila de um dia lotado: se alguém cancelar, a vaga é oferecida a ela."""
        entry = checked(
            await waitlist.post(
                "/entries",
                json={
                    "business_id": str(business_id),
                    "professional_id": str(professional_id),
                    "service_id": str(service_id),
                    "day": str(day),
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                },
            )
        )
        return {"position": entry["position"]}

    @mcp.tool()
    async def cancel_booking(booking_id: UUID) -> dict[str, str]:
        """Cancela um agendamento confirmado; o horário volta a ficar livre."""
        cancelled = checked(await booking.post(f"/bookings/{booking_id}/cancel"))
        return {"booking_id": cancelled["id"], "status": cancelled["status"]}

    return mcp
