# Reuse the locally verified CUDA runtime; do not replace its PyTorch build.
FROM deepmi/fastsurfer@sha256:11d594ae6fea7b1dde5b66ba5124b6295c4eedf1f401e21c7319c22eefd55c50
USER root
RUN python3 -m pip install --no-cache-dir pydantic==2.13.5 pandas==2.3.3 SimpleITK==2.5.6
WORKDIR /workspace
USER 1000:1000
ENTRYPOINT ["python3"]
