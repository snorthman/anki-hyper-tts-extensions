Contributed by @FlyingCowMooMoo


https://github.com/OHF-Voice/piper1-gpl is quite a nice local tool to run, which can create some nice sounding results.


I was going to add some tests, but without running a local instance, itwould not make much sense, let me know if you would like to to include some tests either via mocking piper1-gpl or by including a local docker service.


You can test it locally, below please find the a Dockerfile and a docker compose file

<details>
  <summary>Dockerfile</summary>

```Dockerfile
FROM python:3.12-slim AS build

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        ninja-build \
        git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone --depth 1 https://github.com/OHF-Voice/piper1-gpl.git . && \
    pip install --no-cache-dir .[http]

# ---------------------------------------------------------------------------
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

# ---------------------------------------------------------------------------
# Download German voices from HuggingFace
# ---------------------------------------------------------------------------
ARG VOICE_URL=https://huggingface.co/rhasspy/piper-voices/resolve/main

RUN mkdir -p /data && \
    for voice in \
        "de/de_DE/thorsten/medium/de_DE-thorsten-medium" \
        # "de/de_DE/thorsten/high/de_DE-thorsten-high" \
        # "de/de_DE/thorsten/low/de_DE-thorsten-low" \
        # "de/de_DE/thorsten_emotional/medium/de_DE-thorsten_emotional-medium" \
        # "de/de_DE/kerstin/low/de_DE-kerstin-low" \
        # "de/de_DE/karlsson/low/de_DE-karlsson-low" \
        "de/de_DE/eva_k/x_low/de_DE-eva_k-x_low" \
        # "de/de_DE/ramona/low/de_DE-ramona-low" \
        # "de/de_DE/pavoque/low/de_DE-pavoque-low" \
    ; do \
        name="${voice##*/}"; \
        curl -fSL "${VOICE_URL}/${voice}.onnx?download=true"      -o "/data/${name}.onnx"; \
        curl -fSL "${VOICE_URL}/${voice}.onnx.json?download=true"  -o "/data/${name}.onnx.json"; \
    done

# Remove curl – no longer needed at runtime
RUN apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

EXPOSE 5000

ENTRYPOINT ["python3", "-m", "piper.http_server", "--host", "0.0.0.0", "--data-dir", "/data"]
CMD ["--model", "/data/de_DE-thorsten-medium.onnx"]

```
</details>


<details>
  <summary>compose.yaml</summary>

```yaml
services:
  piper-tts:
    container_name: piper-tts
    build: .
    restart: unless-stopped
    ports:
      - "5100:5000"
    volumes:
      - /etc/localtime:/etc/localtime:ro
    environment:
      - TZ=Europe/Berlin

```
</details>



<img width="586" height="175" alt="image" src="https://github.com/user-attachments/assets/6e437166-1ddb-4564-b31e-59a1718d33f4" />

<img width="1360" height="769" alt="image" src="https://github.com/user-attachments/assets/329dbee2-811f-4149-907f-e7e97813a2d3" />
