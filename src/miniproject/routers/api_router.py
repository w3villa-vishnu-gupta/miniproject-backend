from fastapi import APIRouter

from miniproject.controllers.auth_controller import router as auth_router
from miniproject.controllers.library_controller import router as library_router
from miniproject.controllers.student_controller import router as student_router
from miniproject.controllers.book_controller import router as book_router
from miniproject.controllers.payment_controller import router as payment_router
from miniproject.controllers.chat_controller import router as chat_router

# Aggregated central router managing all domain routes
api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(library_router)
api_router.include_router(student_router)
api_router.include_router(book_router)
api_router.include_router(payment_router)
api_router.include_router(chat_router)
