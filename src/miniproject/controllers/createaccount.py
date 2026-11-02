"""
createaccount.py - Central Aggregator and Backward Compatibility Facade.

This module aggregates the domain controllers (auth, libraries, students, books,
payments, and chat) and re-exports all routes, schemas, and handlers so that
no URL routes, imports, or existing behaviors break.
"""

from miniproject.routers.api_router import api_router as router

# Re-export authentication & owner endpoints and models
from miniproject.controllers.auth_controller import (
    router as auth_router,
    request_magic_link,
    confirm_magic_link,
    direct_magic_callback,
    create_account,
    login,
    get_all_owners,
    get_owner_data,
    update_owner_data,
    update_profile_pic,
    get_profile_pic_url,
    MagicLinkRequest,
    MagicLinkConfirmRequest,
    OwnerProfileUpdate,
    password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

# Re-export library endpoints
from miniproject.controllers.library_controller import (
    router as library_router,
    get_owner_libraries,
    add_library,
)

# Re-export student endpoints
from miniproject.controllers.student_controller import (
    router as student_router,
    addstudent,
    get_all_students,
    update_student_info,
    delete_student,
    get_student,
)

# Re-export book & assignment endpoints
from miniproject.controllers.book_controller import (
    router as book_router,
    add_book,
    get_all_books,
    update_book,
    delete_book,
    get_single_book,
    assign_book,
    get_assigned_books,
    return_assigned_book,
    delete_assignment,
)

# Re-export payment & subscription endpoints
from miniproject.controllers.payment_controller import (
    router as payment_router,
    create_razorpay_order,
    verify_payment,
    get_current_subscription,
    plans,
    VerifyPaymentRequest,
)

# Re-export chat & AI assistant endpoints
from miniproject.controllers.chat_controller import (
    router as chat_router,
    chat_api,
    get_user_sessions,
    get_chat_history,
    create_session_title,
    get_titles,
    ChatMessageRequest,
)

__all__ = [
    "router",
    "auth_router",
    "library_router",
    "student_router",
    "book_router",
    "payment_router",
    "chat_router",
    "request_magic_link",
    "confirm_magic_link",
    "direct_magic_callback",
    "create_account",
    "login",
    "get_all_owners",
    "get_owner_data",
    "update_owner_data",
    "update_profile_pic",
    "get_profile_pic_url",
    "MagicLinkRequest",
    "MagicLinkConfirmRequest",
    "OwnerProfileUpdate",
    "password_hash",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "get_owner_libraries",
    "add_library",
    "addstudent",
    "get_all_students",
    "update_student_info",
    "delete_student",
    "get_student",
    "add_book",
    "get_all_books",
    "update_book",
    "delete_book",
    "get_single_book",
    "assign_book",
    "get_assigned_books",
    "return_assigned_book",
    "delete_assignment",
    "create_razorpay_order",
    "verify_payment",
    "get_current_subscription",
    "plans",
    "VerifyPaymentRequest",
    "chat_api",
    "get_user_sessions",
    "get_chat_history",
    "create_session_title",
    "get_titles",
    "ChatMessageRequest",
]
