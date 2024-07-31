# urls.py

from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),    
    
    path('view_top_artists/', views.view_top_artists, name='view_top_artists'),
    path('view_top_artists/<str:time_range>/', views.view_top_artists, name='view_top_artists_time'),
    
    path('view_top_genres/', views.view_top_genres, name='view_top_genres'),
    path('view_top_genres/<str:time_range>/', views.view_top_genres, name='view_top_genres_time'),
    
    path('view_top_songs/', views.view_top_songs, name='view_top_songs'),
    path('view_top_songs/<str:time_range>/', views.view_top_songs, name='view_top_songs_time'),
    
    path('create_genre_playlist/', views.create_genre_playlist, name='create_genre_playlist'),
    path('create_recommendation_playlist/', views.create_recommendation_playlist_from_playlist, name='create_recommendation_playlist'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
