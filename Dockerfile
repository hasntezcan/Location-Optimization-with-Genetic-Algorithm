FROM node:20-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jdk maven python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

COPY pom.xml ./
COPY src ./src
RUN mvn -q -DskipTests compile

COPY parcel-locker-ui/package*.json ./parcel-locker-ui/
WORKDIR /app/parcel-locker-ui
RUN npm ci

WORKDIR /app
COPY . .

WORKDIR /app/parcel-locker-ui
RUN npm run build

ENV PROJECT_ROOT=/app
ENV UI_ROOT=/app/parcel-locker-ui
ENV GA_CANDIDATE_CSV=data/candidate_points.csv
ENV GA_DISTANCE_MATRIX=data/kadikoy_distance_meters_nxn.npy
ENV GA_OUTPUT_DIR=output
ENV UI_MOCK_DIR=parcel-locker-ui/public/mock
ENV MAVEN_CMD=mvn
ENV PYTHON_CMD=python3
ENV GA_MAX_RUNTIME_MS=900000
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

EXPOSE 3000

CMD ["npm", "run", "start"]
