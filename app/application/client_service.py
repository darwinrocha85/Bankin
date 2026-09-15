"""Casos de uso relacionados con Clientes.

Esta capa orquesta la lógica de negocio usando el puerto ClientRepository,
sin saber (ni importarle) si detrás hay SQLite, Postgres o memoria.
"""
from __future__ import annotations

from app.domain.models import Client, Role
from app.domain.ports import ClientRepository


class ClientNotFoundError(Exception):
    pass


class ClientService:
    def __init__(self, repository: ClientRepository) -> None:
        self._repository = repository

    def create_client(
        self, name: str, username: str, product_id: int, role: Role = Role.CLIENT
    ) -> Client:
        client = Client(name=name, username=username, product_id=product_id, role=role)
        return self._repository.save(client)

    def list_clients(self) -> list[Client]:
        return self._repository.find_all()

    def get_client(self, client_id: int) -> Client:
        client = self._repository.find_by_id(client_id)
        if client is None:
            raise ClientNotFoundError(f"No existe el cliente {client_id}")
        return client

    def find_by_name(self, name: str) -> list[Client]:
        return self._repository.find_by_name(name)

    def update_client(self, client_id: int, name: str, username: str, product_id: int) -> Client:
        existing = self.get_client(client_id)
        existing.name = name
        existing.username = username
        existing.product_id = product_id
        return self._repository.save(existing)

    def delete_client(self, client_id: int) -> None:
        # Se valida que exista antes de borrar, para poder devolver un 404 claro.
        self.get_client(client_id)
        self._repository.delete_by_id(client_id)
