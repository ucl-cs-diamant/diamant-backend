FROM python:3.8
#RUN apt-get update
#RUN apt-get install build-essential git -y
#RUN apt-get install python3 python3-dev python3-venv python3-pip python3-wheel -y
#RUN python3 -m pip install numpy requests tqdm
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
RUN pip3 install uvicorn
COPY . .
CMD ["python3", "-m", "Diamant.asgi:application", "-k", "uvicorn.workers.UvicornWorker"]
