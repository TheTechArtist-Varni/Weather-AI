
import streamlit as st
import requests
import ollama

st.set_page_config(
    page_title="Weather AI",
    page_icon="🌦️",
    layout="centered"
)

st.title("WeatherEXPlo")
st.caption("Ask about the weather anywhere in the world.")

# Store conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# input bar at the bottom
if prompt := st.chat_input("Ask about the weather in any city..."):

    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Checking the latest weather..."):

                # Extract a city using Ollama
                extraction = ollama.chat(
                    model="llama3.2",
                    messages=[{
                        "role": "user",
                        "content": f"""
                        Extract the city and country from this weather
                        question: {prompt}

                        Return ONLY the city and country, separated by
                        a comma. If no location is given, return NONE.

                        Examples:
                        What's the weather in Dubai? -> Dubai, UAE
                        Is it raining in London? -> London, UK
                        """
                    }]
                )

                location = extraction["message"]["content"].strip()

                if location.upper() == "NONE" or not location:
                    answer = (
                        "Which city or location would you like to "
                        "check? For example, ask about Dubai or London."
                    )
                else:
                    # Geocode the location
                    geo = requests.get(
                        "https://geocoding-api.open-meteo.com/v1/search",
                        params={
                            "name": location.split(",")[0].strip(),
                            "count": 10,
                            "language": "en"
                        },
                        timeout=15
                    )
                    geo.raise_for_status()
                    results = geo.json().get("results", [])

                    # Narrow results using the country, if available
                    country_hint = (
                        location.split(",", 1)[1].strip().lower()
                        if "," in location else ""
                    )

                    if country_hint and results:
                        matches = [
                            p for p in results
                            if country_hint in p.get(
                                "country", ""
                            ).lower()
                            or country_hint in p.get(
                                "country_code", ""
                            ).lower()
                        ]
                        if matches:
                            results = matches

                    if not results:
                        answer = (
                            f"I couldn't find **{location}**. "
                            "Please try another city and country."
                        )
                    else:
                        place = results[0]

                        # Retrieve current weather
                        response = requests.get(
                            "https://api.open-meteo.com/v1/forecast",
                            params={
                                "latitude": place["latitude"],
                                "longitude": place["longitude"],
                                "current": (
                                    "temperature_2m,"
                                    "relative_humidity_2m,"
                                    "apparent_temperature,"
                                    "precipitation,"
                                    "wind_speed_10m,"
                                    "weather_code"
                                ),
                                "timezone": "auto"
                            },
                            timeout=15
                        )
                        response.raise_for_status()
                        current = response.json()["current"]

                        codes = {
                            0: "Clear sky",
                            1: "Mainly clear",
                            2: "Partly cloudy",
                            3: "Overcast",
                            45: "Fog",
                            48: "Rime fog",
                            51: "Light drizzle",
                            53: "Drizzle",
                            55: "Heavy drizzle",
                            61: "Light rain",
                            63: "Moderate rain",
                            65: "Heavy rain",
                            71: "Light snow",
                            73: "Moderate snow",
                            75: "Heavy snow",
                            80: "Rain showers",
                            81: "Rain showers",
                            82: "Heavy rain showers",
                            95: "Thunderstorm",
                            96: "Thunderstorm with hail",
                            99: "Thunderstorm with hail"
                        }

                        condition = codes.get(
                            current["weather_code"],
                            "Variable conditions"
                        )

                        # Give Ollama actual retrieved weather data
                        weather_prompt = f"""
                        Answer the user's weather question naturally.
                        Use only the weather measurements provided.
                        Give a concise, useful response with practical advice.
                        Do not invent measurements.

                        User question: {prompt}
                        Location: {place['name']}, {
                            place.get('country', '')
                        }
                        Local time of data: {current['time']}
                        Conditions: {condition}
                        Temperature: {current['temperature_2m']} °C
                        Feels like: {current['apparent_temperature']} °C
                        Humidity: {current['relative_humidity_2m']}%
                        Wind: {current['wind_speed_10m']} km/h
                        Precipitation: {current['precipitation']} mm
                        """

                        result = ollama.chat(
                            model="llama3.2",
                            messages=[{
                                "role": "user",
                                "content": weather_prompt
                            }]
                        )

                        answer = (
                            f"### {place['name']}, "
                            f"{place.get('country', '')}\n\n"
                            f"**{condition} · "
                            f"{current['temperature_2m']} °C**\n\n"
                            f"Feels like **{current['apparent_temperature']} °C** "
                            f" · Humidity **{current['relative_humidity_2m']}%**\n\n"
                            f"Wind **{current['wind_speed_10m']} km/h** "
                            f" · Rain **{current['precipitation']} mm**\n\n"
                            f"---\n\n"
                            f"{result['message']['content']}\n\n"
                            f"---\n\n"
                            f"*Weather data: Open-Meteo · "
                            f"Timestamp: {current['time']}*"
                        )

        except requests.RequestException:
            answer = (
                "I couldn't retrieve weather data right now. "
                "Please check your internet connection and try again."
            )
        except Exception as e:
            answer = (
                "Something went wrong. Check that Ollama is running "
                "and the llama3.2 model is installed.\n\n"
                f"Details: `{e}`"
            )

        st.markdown(answer)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )
