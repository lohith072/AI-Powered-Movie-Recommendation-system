import streamlit as st
import pickle
import pandas as pd
import requests
import numpy as np

API_KEY = "a05e6c0ea08eef814088f3ce20670057"


def fetch_movie_details(movie_id):
    """Fetches movie details including poster, overview, rating, trailer link, streaming providers, and cast."""
    movie_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US&append_to_response=videos,credits"
    provider_url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers?api_key={API_KEY}"

    movie_data = requests.get(movie_url).json()
    provider_data = requests.get(provider_url).json()

    # Extract movie details
    poster_url = "https://image.tmdb.org/t/p/w500/" + movie_data.get('poster_path', '')
    overview = movie_data.get('overview', 'No overview available.')
    rating = movie_data.get('vote_average', 0)
    release_year = movie_data.get('release_date', '')[:4]  # Extracts only the year

    # Get YouTube trailer
    trailer_url = None
    for video in movie_data.get("videos", {}).get("results", []):
        if video["site"] == "YouTube" and video["type"] == "Trailer":
            trailer_url = f"https://www.youtube.com/watch?v={video['key']}"
            break

    # Get streaming providers with direct links
    ott_providers = []
    if 'results' in provider_data and 'IN' in provider_data['results']:  # Check availability in India
        if 'flatrate' in provider_data['results']['IN']:
            for provider in provider_data['results']['IN']['flatrate']:
                provider_name = provider["provider_name"]
                provider_logo = f"https://image.tmdb.org/t/p/w500/{provider['logo_path']}"
                provider_link = provider_data['results']['IN'].get('link', '#')  # Direct streaming link
                ott_providers.append((provider_name, provider_logo, provider_link))

    # Fetch top 5 cast members with profile images
    cast = []
    for member in movie_data.get("credits", {}).get("cast", [])[:5]:  # First 5 cast members
        cast_name = member.get("name", "Unknown")
        cast_profile = "https://image.tmdb.org/t/p/w500/" + member["profile_path"] if member.get("profile_path") else "https://via.placeholder.com/100"
        cast.append((cast_name, cast_profile))

    return poster_url, overview, rating, trailer_url, ott_providers, release_year, cast


def recommend_from_favorites(favorite_movies):
    """Recommends movies based on multiple favorite movies."""
    movie_indices = [movies[movies['title'] == movie].index[0] for movie in favorite_movies]

    # Aggregate similarity scores from all selected movies
    total_similarities = np.sum([similarity[i] for i in movie_indices], axis=0)

    recommended_indices = sorted(list(enumerate(total_similarities)), reverse=True, key=lambda x: x[1])

    recommended_movies = []
    added_movies = set()

    for i, _ in recommended_indices:
        title = movies.iloc[i].title
        if title not in favorite_movies and title not in added_movies:  # Avoid recommending already selected favorites
            movie_id = movies.iloc[i].movie_id
            poster, overview, rating, trailer, ott_providers, release_year, cast = fetch_movie_details(movie_id)

            if rating > 6:  # Only recommend movies with IMDb rating above 6
                recommended_movies.append((title, poster, overview, rating, trailer, ott_providers, release_year, cast))
                added_movies.add(title)

            if len(recommended_movies) == 5:
                break

    return recommended_movies


# Load movie data
movies_dict = pickle.load(open('movie_dict.pkl', 'rb'))
movies = pd.DataFrame(movies_dict)

similarity = pickle.load(open('similarity.pkl', 'rb'))

# Streamlit UI
st.title('🎬 Movie Recommender System')

# User choice: Single Movie vs Multiple Movies
option = st.radio("Choose Recommendation Type:", ("Find Similar Movies", "Get Personalized Recommendations"))

if option == "Get Personalized Recommendations":
    st.subheader("Select your 5 favorite movies:")
    favorite_movies = st.multiselect("Choose exactly 5 movies:", movies['title'].values, default=[])

    if st.button('Get Recommendations') and len(favorite_movies) == 5:
        recommendations = recommend_from_favorites(favorite_movies)

        if recommendations:
            st.subheader("🎯 Personalized Recommendations:")
            for title, poster, overview, rating, trailer, ott_providers, release_year, cast in recommendations:
                with st.container():
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.image(poster, use_container_width=True)
                    with col2:
                        st.subheader(f"{title} ({release_year})")
                        st.write(f"**IMDb Rating:** {rating} ⭐")
                        st.write(f"**Overview:** {overview}")

                        # Display cast members
                        if cast:
                            st.write("**Top Cast:**")
                            cast_cols = st.columns(len(cast))
                            for idx, (cast_name, cast_image) in enumerate(cast):
                                with cast_cols[idx]:
                                    st.image(cast_image, width=70, caption=cast_name)

                        # YouTube trailer button
                        if trailer:
                            st.markdown(
                                f'<a href="{trailer}" target="_blank">'
                                f'<img src="https://www.freepnglogos.com/uploads/youtube-play-red-logo-png-transparent-background-6.png" width="40"/> Watch Trailer</a>',
                                unsafe_allow_html=True
                            )

                        # Show OTT providers
                        if ott_providers:
                            st.write("**Available on:**")
                            cols = st.columns(len(ott_providers))
                            for idx, (name, logo, link) in enumerate(ott_providers):
                                with cols[idx]:
                                    st.markdown(
                                        f'<a href="{link}" target="_blank">'
                                        f'<img src="{logo}" width="60"/><br><small>{name}</small></a>',
                                        unsafe_allow_html=True
                                    )

                    st.markdown("---")

        else:
            st.warning("No suitable recommendations found with IMDb rating above 6.")

elif option == "Find Similar Movies":
    selected_movie_name = st.selectbox("Select a movie to get recommendations:", movies['title'].values)

    if st.button('Recommend'):
        recommendations = recommend_from_favorites([selected_movie_name])

        for title, poster, overview, rating, trailer, ott_providers, release_year, cast in recommendations:
            with st.container():
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.image(poster, use_container_width=True)
                with col2:
                    st.subheader(f"{title} ({release_year})")
                    st.write(f"**IMDb Rating:** {rating} ⭐")
                    st.write(f"**Overview:** {overview}")

                    # Display cast members
                    if cast:
                        st.write("**Top Cast:**")
                        cast_cols = st.columns(len(cast))
                        for idx, (cast_name, cast_image) in enumerate(cast):
                            with cast_cols[idx]:
                                st.image(cast_image, width=70, caption=cast_name)

                    # YouTube trailer button
                    if trailer:
                        st.markdown(
                            f'<a href="{trailer}" target="_blank">'
                            f'<img src="https://www.freepnglogos.com/uploads/youtube-play-red-logo-png-transparent-background-6.png" width="40"/> Watch Trailer</a>',
                            unsafe_allow_html=True
                        )

                    # Show OTT providers
                    if ott_providers:
                        st.write("**Available on:**")
                        cols = st.columns(len(ott_providers))
                        for idx, (name, logo, link) in enumerate(ott_providers):
                            with cols[idx]:
                                st.markdown(
                                    f'<a href="{link}" target="_blank">'
                                    f'<img src="{logo}" width="60"/><br><small>{name}</small></a>',
                                    unsafe_allow_html=True
                                )

                st.markdown("---")
