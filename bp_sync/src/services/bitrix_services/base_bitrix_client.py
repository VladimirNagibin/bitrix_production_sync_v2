from typing import Any, TypeVar, cast

from fastapi import status

from core import settings
from core.exceptions.bitrix24 import BitrixApiError
from core.logger import logger
from schemas.base_schemas import CommonFieldMixin, ListResponseSchema

from .bitrix_api_client import BitrixAPIClient
from .decorators import handle_bitrix_errors


# ===== Константы =====
METHODS_WITH_NESTED_RESULT: tuple[str, ...] = ("add", "get")

# ===== Типы =====
SchemaTypeCreate = TypeVar("SchemaTypeCreate", bound=CommonFieldMixin)
SchemaTypeUpdate = TypeVar("SchemaTypeUpdate", bound=CommonFieldMixin)


class BaseBitrixEntityClient[
    SchemaTypeCreate: CommonFieldMixin,
    SchemaTypeUpdate: CommonFieldMixin,
]:
    """
    Базовый клиент для работы с сущностями Bitrix24.

    Предоставляет CRUD-операции для типовых сущностей CRM
    (сделки, контакты, товары и т.д.) с поддержкой универсальных методов
    crm.item.* и стандартных методов crm.{entity_name}.*.
    """

    # ----- Атрибуты класса (должны быть переопределены в наследниках) -----
    entity_name: str  # Название сущности (например, "deal", "contact")
    create_schema: type[SchemaTypeCreate]  # Схема для создания
    update_schema: type[SchemaTypeUpdate]  # Схема для обновления

    def __init__(self, bitrix_client: BitrixAPIClient) -> None:
        """
        Инициализирует клиент сущности.

        Args:
            bitrix_client: Экземпляр API-клиента Bitrix24.
        """
        self.bitrix_client = bitrix_client

    def _get_method_name(
        self,
        action: str,
        entity_type_id: int | None,
        use_crm_prefix: bool = True,
    ) -> str:
        """
        Формирует имя метода API в зависимости от типа сущности.

        Args:
            action: Действие (add, get, update, delete, list).
            entity_type_id: ID типа сущности для универсальных методов
                            (crm.item.*).
            use_crm_prefix: Добавлять префикс "crm.".

        Returns:
            Имя метода, например: "crm.deal.add" или "crm.item.add".
        """
        prefix = "crm." if use_crm_prefix else ""
        if entity_type_id is not None:
            return f"{prefix}item.{action}"
        return f"{prefix}{self.entity_name}.{action}"

    def _prepare_request_params(
        self,
        entity_id: int | str | None = None,
        fields: dict[str, Any] | None = None,
        entity_type_id: int | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """
        Подготавливает параметры для API-запроса.

        Args:
            entity_id: ID сущности (для get, update, delete).
            fields: Данные сущности (для add, update).
            entity_type_id: ID типа сущности (для универсальных методов).
            extra_params: Дополнительные параметры
                          (select, filter, order, start).
        Returns:
            Словарь параметров для передачи в call_api.
        """
        # params = kwargs.copy()
        params = {k: v for k, v in extra_params.items() if v is not None}
        if entity_id is not None:
            params["id"] = entity_id

        if fields is not None:
            params["fields"] = fields
        if entity_type_id:
            params["entityTypeId"] = entity_type_id

        return params

    def _extract_result_from_response(
        self,
        response: dict[str, Any],
        action: str,
        entity_id: int | str | None = None,
        entity_type_id: int | None = None,
        use_crm_prefix: bool = True,
    ) -> Any:
        """
        Извлекает результат из ответа API, обрабатывая различные форматы.

        Args:
            response: Ответ от call_api.
            action: Выполненное действие.
            entity_id: ID сущности (для логирования).
            entity_type_id: ID типа сущности.
            use_crm_prefix: Используется ли префикс "crm.".

        Returns:
            Извлечённый результат (обычно словарь или список).

        Raises:
            BitrixApiError: Если результат отсутствует или произошла ошибка
                            API.
        """
        raw_result = response.get("result")  # может быть dict, list и т.д.
        extracted_data = None

        # Обработка универсальных методов crm.item.*
        if (
            entity_type_id
            and action in METHODS_WITH_NESTED_RESULT
            and isinstance(raw_result, dict)
        ):
            extracted_data = cast("dict[str, Any]", raw_result).get("item")
        # Обработка методов для товаров (без префикса crm)
        elif not use_crm_prefix and action in METHODS_WITH_NESTED_RESULT:
            if isinstance(raw_result, dict):
                extracted_data = cast("dict[str, Any]", raw_result).get(
                    "product"
                )
        else:
            extracted_data = raw_result

        if not extracted_data:
            error = response.get("error", "Unknown error")
            error_description = response.get(
                "error_description", "Unknown error"
            )
            status_code = response.get(
                "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            entity_ref = f"ID={entity_id}" if entity_id else ""
            logger.error(
                f"Failed to {action} {self.entity_name} {entity_ref}: "
                f"{error} - {error_description}"
            )

            if action == "get":
                raise BitrixApiError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=(
                        f"Failed to {action} {self.entity_name} "
                        f"{entity_ref}: {error}"
                    ),
                    error_description=error_description,
                    error=error,
                )
            raise BitrixApiError(
                status_code=status_code,
                message=f"Failed to {action} {self.entity_name}",
            )

        return extracted_data

    def _log_success(
        self, action: str, entity_id: int | str | None = None
    ) -> None:
        """Логирует успешное выполнение операции."""
        if entity_id:
            logger.info(
                f"{self.entity_name.capitalize()} {action} successfully: "
                f"ID={entity_id}"
            )
        else:
            logger.info(
                f"{self.entity_name.capitalize()} {action} successfully"
            )

    # ----- Публичные CRUD-методы -----

    @handle_bitrix_errors()
    async def create(
        self,
        data: SchemaTypeUpdate,
        entity_type_id: int | None = None,
        use_crm_prefix: bool = True,
    ) -> int | str | None:
        """
        Создаёт новую сущность в Bitrix24.

        Args:
            data: Данные для создания (схема с методом to_bitrix_dict()).
            entity_type_id: ID типа сущности (для crm.item.add).
            use_crm_prefix: Добавлять префикс "crm.".

        Returns:
            ID созданной сущности или None.

        Raises:
            BitrixApiError: При ошибке API.
        """
        entity_title = (
            getattr(data, "title", None) or getattr(data, "name", "") or ""
        )
        logger.info(f"Creating new {self.entity_name}: {entity_title}")
        method = self._get_method_name("add", entity_type_id, use_crm_prefix)
        params = self._prepare_request_params(
            fields=data.to_bitrix_dict(),
            entity_type_id=entity_type_id,
        )

        response = await self.bitrix_client.call_api(
            method=method, params=params
        )
        result = self._extract_result_from_response(
            response, "add", entity_type_id=entity_type_id
        )
        if entity_type_id:
            # Универсальный метод: ожидаем словарь с полем "id"
            if isinstance(result, dict):
                created_id = cast("dict[str, Any]", result).get("id")
                if created_id is None:
                    logger.error(
                        f"Missing 'id' field in create response: {result}"
                    )
                    raise BitrixApiError(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        message=(
                            "Invalid response from Bitrix24: missing 'id' "
                            "field"
                        ),
                    )
            else:
                logger.error(
                    f"Expected dict, got {type(result).__name__}: {result}"
                )
                raise BitrixApiError(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Invalid response format from Bitrix24",
                )
        else:
            # Стандартный метод: возвращает непосредственно ID
            if isinstance(result, int | str):
                created_id = result
            else:
                logger.error(
                    f"Expected int or str, got {type(result).__name__}: "
                    f"{result}"
                )
                raise BitrixApiError(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    error_description="Invalid response format from Bitrix24",
                )
        self._log_success("created", created_id)
        return created_id  # type: ignore[no-any-return]

    @handle_bitrix_errors()
    async def get(
        self,
        entity_id: int | str,
        entity_type_id: int | None = None,
        use_crm_prefix: bool = True,
    ) -> SchemaTypeCreate:
        """
        Получает сущность по ID.

        Args:
            entity_id: ID сущности.
            entity_type_id: ID типа сущности (для crm.item.get).
            use_crm_prefix: Добавлять префикс "crm.".

        Returns:
            Схема сущности.

        Raises:
            BitrixApiError: Если сущность не найдена или ошибка API.
        """
        logger.debug(f"Fetching {self.entity_name} ID={entity_id}")

        method = self._get_method_name("get", entity_type_id, use_crm_prefix)
        params = self._prepare_request_params(
            entity_id=entity_id,
            entity_type_id=entity_type_id,
        )
        response = await self.bitrix_client.call_api(
            method=method, params=params
        )
        result = self._extract_result_from_response(
            response,
            "get",
            entity_id,
            entity_type_id,
            use_crm_prefix,
        )
        return self.create_schema(**result)

    @handle_bitrix_errors()
    async def update(
        self,
        data: SchemaTypeUpdate,
        entity_type_id: int | None = None,
        use_crm_prefix: bool = True,
    ) -> bool:
        """
        Обновляет существующую сущность.

        Args:
            data: Данные для обновления (должны содержать external_id).
            entity_type_id: ID типа сущности (для crm.item.update).
            use_crm_prefix: Добавлять префикс "crm.".

        Returns:
            True, если обновление успешно.

        Raises:
            BitrixApiError: Если не передан external_id или при ошибке API.
        """
        if not data.external_id:
            message_error = (
                f"{self.entity_name.capitalize()} ID is required for update"
            )
            logger.error(message_error)
            raise ValueError(message_error)

        entity_id = data.external_id
        logger.info(f"Updating {self.entity_name} ID={entity_id}")

        method = self._get_method_name(
            "update", entity_type_id, use_crm_prefix
        )
        params = self._prepare_request_params(
            entity_id=entity_id,
            fields=data.to_bitrix_dict(),
            entity_type_id=entity_type_id,
        )
        response = await self.bitrix_client.call_api(
            method=method, params=params
        )
        # Определяем успешность в зависимости от типа метода
        if entity_type_id:
            success = bool(response.get("result", {}).get("item"))
        else:
            success = bool(response.get("result"))

        if success:
            self._log_success("updated", entity_id)
            return True

        error_code = response.get("error", "UPDATING_ENTITY_ERROR")
        error_desc = response.get("error_description", "Unknown error")
        status_code = response.get("status_code", status.HTTP_400_BAD_REQUEST)

        logger.error(
            f"Failed to update {self.entity_name} ID={entity_id}: "
            f"{error_code} - {error_desc}"
        )
        raise BitrixApiError(
            status_code=status_code,
            error=error_code,
            error_description=error_desc,
            message=f"Failed to update {self.entity_name}",
        )

    @handle_bitrix_errors()
    async def delete(
        self,
        entity_id: int | str,
        entity_type_id: int | None = None,
        use_crm_prefix: bool = True,
    ) -> bool:
        """
        Удаляет сущность по ID.

        Args:
            entity_id: ID сущности.
            entity_type_id: ID типа сущности (для crm.item.delete).
            use_crm_prefix: Добавлять префикс "crm.".

        Returns:
            True, если удаление успешно.
        """
        logger.info(f"Deleting {self.entity_name} ID={entity_id}")

        method = self._get_method_name(
            "delete", entity_type_id, use_crm_prefix
        )
        params = self._prepare_request_params(
            entity_id=entity_id, entity_type_id=entity_type_id
        )

        response = await self.bitrix_client.call_api(
            method=method, params=params
        )
        if entity_type_id:
            # Для универсальных методов (crm.item.delete)
            # Успешный ответ может содержать пустой массив в result
            success = "result" in response and response["result"] is not False
        else:
            # Для стандартных методов
            success = response.get("result") is True

        if success:
            self._log_success("deleted", entity_id)
            return True

        error_code = response.get("error", "DELETE_ENTITY_ERROR")
        error_desc = response.get("error_description", "Unknown error")
        status_code = response.get("status_code", status.HTTP_400_BAD_REQUEST)

        logger.error(
            f"Failed to delete {self.entity_name} ID={entity_id}: "
            f"{error_code} - {error_desc}"
        )
        raise BitrixApiError(
            status_code=status_code,
            error=error_code,
            error_description=error_desc,
            message=f"Failed to delete {self.entity_name}",
        )

    @handle_bitrix_errors()
    async def list(
        self,
        select: list[str] | None = None,
        filter_entity: dict[str, Any] | None = None,
        order: dict[str, str] | None = None,
        start: int = 0,
        entity_type_id: int | None = None,
        use_crm_prefix: bool = True,
    ) -> ListResponseSchema[SchemaTypeUpdate]:
        """Список сущностей с фильтрацией

        Получает список сущностей из Bitrix24 с возможностью фильтрации,
        сортировки и постраничной выборки.

        Args:
            select: Список полей для выборки.
                - Может содержать маски:
                    '*' - все основные поля (без пользовательских и
                          множественных)
                    'UF_*' - все пользовательские поля (без множественных)
                - По умолчанию выбираются все поля ('*' + 'UF_*')
                - Доступные поля: `crm.{entity_name}.fields`
                - Пример: ["ID", "TITLE", "OPPORTUNITY"]

            filter: Фильтр для выборки сделок.
                - Формат: {поле: значение}
                - Поддерживаемые префиксы для операторов:
                    '>=' - больше или равно
                    '>'  - больше
                    '<=' - меньше или равно
                    '<'  - меньше
                    '@'  - IN (значение должно быть массивом)
                    '!@' - NOT IN (значение должно быть массивом)
                    '%'  - LIKE (поиск подстроки, % не нужен)
                    '=%' - LIKE с указанием позиции (% в начале)
                    '=%%' - LIKE с указанием позиции (% в конце)
                    '=%%%' - LIKE с подстрокой в любой позиции
                    '='  - равно (по умолчанию)
                    '!=' - не равно
                    '!'  - не равно
                - Не работает с полями типа crm_status, crm_contact ...
                - Пример: {">OPPORTUNITY": 1000, "CATEGORY_ID": 1}

            order: Сортировка результатов.
                - Формат: {поле: направление}
                - Направление: "ASC" (по возрастанию) или "DESC" (по убыванию)
                - Пример: {"TITLE": "ASC", "DATE_CREATE": "DESC"}

            start: Смещение для постраничной выборки.
                - Размер страницы фиксирован: 50 записей
                - Формула: start = (N-1) * 50, где N - номер страницы
                - Пример: для 2-й страницы передать 50

            entity_type_id: ID типа сущности (для crm.item.list).

            use_crm_prefix: Добавлять префикс "crm.".

        Returns:
            ListResponseSchema: Объект с результатами выборки:
                - result: список сущностей
                - total: общее количество сущностей
                - next: смещение для следующей страницы (если есть)

        Raises:
            BitrixApiError: При ошибке API.

        Example:
            Получить сделки с фильтрацией и сортировкой:
            ```python
            deals = await client.list(
                select=["ID", "TITLE", "OPPORTUNITY"],
                filter={
                    "CATEGORY_ID": 1,
                    ">OPPORTUNITY": 10000,
                    "<=OPPORTUNITY": 20000,
                    "@ASSIGNED_BY_ID": [1, 6]
                },
                order={"OPPORTUNITY": "ASC"},
                start=0
            )
            ```

        Bitrix API Example:
            ```bash
            curl -X POST \\
            -H "Content-Type: application/json" \\
            -H "Accept: application/json" \\
            -d '{
                "SELECT": ["ID", "TITLE", "OPPORTUNITY"],
                "FILTER": {
                    "CATEGORY_ID": 1,
                    ">OPPORTUNITY": 10000,
                    "<=OPPORTUNITY": 20000,
                    "@ASSIGNED_BY_ID": [1, 6]
                },
                "ORDER": {"OPPORTUNITY": "ASC"},
                "start": 0
            }' \\
            https://example.bitrix24.ru/rest/user_id/webhook/crm.deal.list
            ```
        """
        logger.debug(
            f"Fetching {self.entity_name} list: "
            f"select={select}, filter={filter_entity}, "
            f"order={order}, start={start}"
        )

        method = self._get_method_name("list", entity_type_id, use_crm_prefix)
        params = self._prepare_request_params(
            entity_type_id=entity_type_id,
            select=select,
            filter=filter_entity,
            order=order,
            start=start,
        )
        response = await self.bitrix_client.call_api(
            method=method, params=params
        )
        result = response.get("result", {})

        # Извлечение элементов в зависимости от типа метода
        if entity_type_id:
            entities = result.get("items", [])
        elif not use_crm_prefix:
            # Методы товаров (crm.product.list) возвращают "products"
            entities = result.get("products", [])
        else:
            entities = result

        total = response.get("total", 0)
        next_page = response.get("next")

        parsed_entities = [
            self.update_schema(**entity) for entity in entities
        ]
        logger.info(
            f"Fetched {len(parsed_entities)} of {total} {self.entity_name}s"
        )
        return ListResponseSchema[SchemaTypeUpdate](
            result=parsed_entities,
            total=total,
            next=next_page,
        )

    # ----- Дополнительные методы -----

    def get_default_create_schema(self, external_id: int | str) -> Any:
        """Возвращает схему создания с заполненным external_id."""
        return self.create_schema.get_default_entity(external_id)

    @handle_bitrix_errors()
    async def send_message_b24(
        self, recipient_id: int, message: str, is_chat: bool = False
    ) -> bool:
        """
        Отправляет сообщение пользователю или в чат Bitrix24.

        Args:
            recipient_id: ID пользователя или ID чата.
            message: Текст сообщения.
            is_chat: Если True, recipient_id считается CHAT_ID, иначе user_id.

        Returns:
            True, если сообщение отправлено успешно, иначе False.
        """
        logger.debug(
            f"Sending message to {recipient_id} (chat={is_chat}): {message}"
        )
        params: dict[str, Any] = {
            "message": message,
            ("CHAT_ID" if is_chat else "user_id"): recipient_id,
        }
        try:
            response = await self.bitrix_client.call_api(
                "im.message.add",
                params=params,
            )
            return bool(response.get("result", False))
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to send message to {recipient_id}: {e}")
            return False

    def get_entity_link(self, external_id: int | str | None) -> str:
        """
        Формирует URL для просмотра сущности в портале Bitrix24.

        Args:
            external_id: ID сущности.

        Returns:
            Полный URL.
        """
        return (
            f"{settings.bitrix24.portal_url}/crm/{self.entity_name}/details/"
            f"{external_id if external_id else ''}/"
        )

    def get_formatted_link(
        self, external_id: int | str | None, titlt: str
    ) -> str:
        """
        Формирует BB-код ссылки на сущность.

        Args:
            external_id: ID сущности.
            title: Текст ссылки.

        Returns:
            Строка вида [url=...]title[/url].
        """
        return f"[url={self.get_entity_link(external_id)}]{titlt}[/url]"

    @handle_bitrix_errors()
    async def execute_batch(
        self, commands: dict[str, Any], halt_on_error: int = 0
    ) -> dict[str, Any]:
        """
        Выполняет батч-запрос (несколько команд за один вызов).

        Args:
            commands: Словарь команд вида {"cmd_name": "method?param=value"}.
            halt_on_error: Остановить выполнение при ошибке (0/1).

        Returns:
            Результат выполнения батча.

        Raises:
            BitrixApiError: При ошибке выполнения.
        """
        method = "batch"
        params: dict[str, Any] = {"halt": halt_on_error, "cmd": commands}
        response = await self.bitrix_client.call_api(
            method=method, params=params
        )

        return cast(
            "dict[str, Any]",
            self._extract_result_from_response(response, method),
        )
