from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("create", views.create, name="create"),
    path("listing/<int:listing_id>", views.listing, name="listing"),
    path("watchlist", views.watchlist, name="watchlist"),
    path("add_to_watchlist/<int:listing_id>", views.add_to_watchlist, name="add_to_watchlist"),
    path('remove_from_watchlist/<int:listing_id>', views.remove_from_watchlist, name='remove_from_watchlist'),
    path('close_listing/<int:listing_id>', views.close_listing, name='close_listing'),
    path('comment/<int:listing_id>', views.comment, name='comment'),
    path('categories', views.categories, name="categories"),
    path('category/<int:category_id>', views.category, name="category"),
    path('listings', views.listings, name="listings"),
    path('profile/<int:user_id>', views.profile, name='profile'),
    path('edit/<int:user_id>', views.edit, name='edit'),
    path('change_password/<int:user_id>', views.change_password, name='change_password'),
]
