from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, Request, status
from loguru import logger
from sqlalchemy.exc import IntegrityError, OperationalError


class BaseController:
    """
    Base Controller class - Blueprint untuk semua controller
    Semua logic bisnis tetap di service layer
    Controller cuma handle request/response formatting dan error handling
    """

    @staticmethod
    def success_response(
        data: Any = None,
        message: str = "Success",
        status_code: int = 200,
        meta: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Standard success response format"""
        response = {
            "success": True,
            "status_code": status_code,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

        if data is not None:
            response["data"] = data

        if meta:
            response["meta"] = meta

        return response

    @staticmethod
    def error_response(
        message: str = "An error occurred",
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> HTTPException:
        """Standard error response format"""
        error_data = {
            "success": False,
            "status_code": status_code,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

        if error_code:
            error_data["error_code"] = error_code

        if details:
            error_data["details"] = details

        return HTTPException(status_code=status_code, detail=error_data)

    @staticmethod
    def paginated_response(
        data: List[Any],
        page: int = 1,
        per_page: int = 10,
        total: int = 0,
        message: str = "Data retrieved successfully",
    ) -> Dict[str, Any]:
        """Standard paginated response format"""
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1

        meta = {
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            }
        }

        return BaseController.success_response(data=data, message=message, meta=meta)

    @staticmethod
    def handle_service_error(
        error: Exception, default_message: str = "Service error"
    ) -> HTTPException:
        """Handle errors dari service layer"""
        logger.error(f"Service error: {error}")
        # Jika error sudah HTTPException, langsung return
        if isinstance(error, HTTPException):
            return error

        # Handle specific error types
        if "not found" in str(error).lower():
            return BaseController.error_response(
                message=str(error),
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="NOT_FOUND",
            )
        elif "already exists" in str(error).lower():
            return BaseController.error_response(
                message=str(error),
                status_code=status.HTTP_409_CONFLICT,
                error_code="ALREADY_EXISTS",
            )
        elif "validation" in str(error).lower():
            return BaseController.error_response(
                message=str(error),
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="VALIDATION_ERROR",
            )
        else:
            return BaseController.error_response(
                message=default_message,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="INTERNAL_ERROR",
                details={"original_error": str(error)},
            )

    @staticmethod
    def validate_request_data(
        data: Any, required_fields: Optional[List[str]] = None
    ) -> None:
        """Basic request validation"""
        if required_fields is None:
            required_fields = []
        if required_fields:
            missing_fields = []
            for field in required_fields:
                if not hasattr(data, field) or getattr(data, field) is None:
                    missing_fields.append(field)

            if missing_fields:
                raise BaseController.error_response(
                    message=f"Missing required fields: {', '.join(missing_fields)}",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    error_code="MISSING_FIELDS",
                )

    @staticmethod
    def log_request(request: Request, action: str, user_id: Optional[int] = None):
        """Log request untuk audit trail"""
        logger.info(
            "Action: %s | IP: %s | User: %s | Method: %s | URL: %s",
            action,
            request.client.host if request.client else "Unknown",
            user_id,
            request.method,
            request.url,
        )


class CRUDController(BaseController):
    """
    Extended base controller untuk CRUD operations
    Blueprint untuk controller yang handle standard CRUD
    """

    @classmethod
    def create_item(
        cls,
        service_method,
        item_data,
        success_message: str = "Item created successfully",
    ):
        """Generic create method"""
        try:
            result = service_method(item_data)
            return cls.success_response(
                data=result,
                message=success_message,
                status_code=status.HTTP_201_CREATED,
            )
        except IntegrityError as e:
            logger.error(f"Database integrity error creating item: {e}")
            raise cls.error_response(
                message="Database constraint violation",
                status_code=status.HTTP_409_CONFLICT,
                error_code="INTEGRITY_ERROR",
            )
        except OperationalError as e:
            logger.error(f"Database connection error creating item: {e}")
            raise cls.error_response(
                message="Database connection error",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code="DATABASE_ERROR",
            )

    @classmethod
    def get_item(
        cls,
        service_method,
        item_id: Union[int, str],
        success_message: str = "Item retrieved successfully",
    ):
        """Generic get single item method"""
        try:
            result = service_method(item_id)
            if not result:
                raise cls.error_response(
                    message="Item not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_code="NOT_FOUND",
                )
            return cls.success_response(data=result, message=success_message)
        except IntegrityError as e:
            logger.error(f"Database integrity error retrieving item: {e}")
            raise cls.error_response(
                message="Database constraint violation",
                status_code=status.HTTP_409_CONFLICT,
                error_code="INTEGRITY_ERROR",
            )
        except OperationalError as e:
            logger.error(f"Database connection error retrieving item: {e}")
            raise cls.error_response(
                message="Database connection error",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code="DATABASE_ERROR",
            )

    @classmethod
    def get_items(cls, service_method, page: int = 1, per_page: int = 10, **filters):
        """Generic get multiple items method with pagination"""
        try:
            skip = (page - 1) * per_page
            items = service_method(skip=skip, limit=per_page, **filters)

            # Jika service return tuple (items, total), handle pagination
            if isinstance(items, tuple):
                items_data, total = items
                return cls.paginated_response(
                    data=items_data, page=page, per_page=per_page, total=total
                )
            else:
                return cls.success_response(
                    data=items, message="Items retrieved successfully"
                )
        except IntegrityError as e:
            logger.error(f"Database integrity error retrieving items: {e}")
            raise cls.error_response(
                message="Database constraint violation",
                status_code=status.HTTP_409_CONFLICT,
                error_code="INTEGRITY_ERROR",
            )
        except OperationalError as e:
            logger.error(f"Database connection error retrieving items: {e}")
            raise cls.error_response(
                message="Database connection error",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code="DATABASE_ERROR",
            )

    @classmethod
    def update_item(
        cls,
        service_method,
        item_id: Union[int, str],
        update_data,
        success_message: str = "Item updated successfully",
    ):
        """Generic update method"""
        try:
            result = service_method(item_id, update_data)
            if not result:
                raise cls.error_response(
                    message="Item not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_code="NOT_FOUND",
                )
            return cls.success_response(data=result, message=success_message)
        except IntegrityError as e:
            logger.error(f"Database integrity error updating item: {e}")
            raise cls.error_response(
                message="Database constraint violation",
                status_code=status.HTTP_409_CONFLICT,
                error_code="INTEGRITY_ERROR",
            )
        except OperationalError as e:
            logger.error(f"Database connection error updating item: {e}")
            raise cls.error_response(
                message="Database connection error",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code="DATABASE_ERROR",
            )

    @classmethod
    def delete_item(
        cls,
        service_method,
        item_id: Union[int, str],
        success_message: str = "Item deleted successfully",
    ):
        """Generic delete method"""
        try:
            success = service_method(item_id)
            if not success:
                raise cls.error_response(
                    message="Item not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_code="NOT_FOUND",
                )
            return cls.success_response(
                data={"deleted_id": item_id}, message=success_message
            )
        except IntegrityError as e:
            logger.error(f"Database integrity error deleting item: {e}")
            raise cls.error_response(
                message="Database constraint violation",
                status_code=status.HTTP_409_CONFLICT,
                error_code="INTEGRITY_ERROR",
            )
        except OperationalError as e:
            logger.error(f"Database connection error deleting item: {e}")
            raise cls.error_response(
                message="Database connection error",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code="DATABASE_ERROR",
            )
