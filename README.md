# docker-rutorrent

Extended rtorrent + ruTorrent Docker image from https://github.com/linuxserver/docker-rutorrent with added sort script.

Once a torrent finishes downloading, [sort.py](/sort.py) is called which moves the torrent's data to a new directory based on its tracker, according to a [yaml config](sort-config.yaml) file, and resumes seeding. To customize the sorting, mount your own sort-config.yaml into /config/rtorrent/sort-config.yaml.
