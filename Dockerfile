FROM linuxserver/rutorrent:v3.9-ls67
RUN pip3 install pyyaml
COPY ["sort-config.yaml", "rtorrent.rc", "/config/rtorrent/"]
COPY sort.py /app/sort.py
