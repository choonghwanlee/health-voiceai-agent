FROM python:3.9-bullseye

# get portaudio and ffmpeg
RUN apt-get update \
        && apt-get install libportaudio2 libportaudiocpp0 portaudio19-dev libasound-dev libsndfile1-dev -y
RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y ffmpeg

WORKDIR /code
COPY requirements.txt /code/
RUN pip install --no-cache-dir --requirement /code/requirements.txt
COPY main.py /code/main.py
COPY event_manager.py /code/event_manager.py
COPY call_transcript_utils.py /code/call_transcript_utils.py
COPY instructions.txt /code/instructions.txt
RUN mkdir -p /code/call_transcripts
RUN mkdir -p /code/db

# Copy the utils directory (and its contents) into the container

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]