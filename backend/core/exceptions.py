from uuid import UUID

class AppException(Exception):
    pass

class EntityNotFoundException(AppException):
    def __init__(self, entity_name: str, entity_id: str | UUID):
        self.entity_name = entity_name
        self.entity_id = entity_id
        super().__init__(f"Entity {entity_name} with ID {entity_id} not found")