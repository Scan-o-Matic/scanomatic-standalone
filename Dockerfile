FROM node:16 as npmbuilder
COPY . /src
WORKDIR /src
RUN npm ci
RUN npm run build

FROM python:3.9
RUN apt-get update
RUN export DEBIAN_FRONTEND=noninteractive \
    && ln -fs /usr/share/zoneinfo/Etc/UTC /etc/localtime \
    && apt-get install -y tzdata \
    && dpkg-reconfigure --frontend noninteractive tzdata
RUN apt-get -y install usbutils software-properties-common
# net-tools & iputils-ping are used in the xml-writer which should be removed soon
RUN apt-get -y install net-tools iputils-ping
RUN apt-get -y install libsane sane-utils libsane-common
# Add scanner id to sane config in case scanimage -L cannot find the scanner automatically
# Epson V800
RUN echo "usb 0x4b8 0x12c" >> /etc/sane.d/epson2.conf
# Epson V700
RUN echo "usb 0x4b8 0x151" >> /etc/sane.d/epson2.conf

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY data/ /tmp/data/
COPY scripts/ /tmp/scripts/
COPY scanomatic/ /tmp/scanomatic/
COPY setup.py /tmp/setup.py
COPY setup_tools.py /tmp/setup_tools.py
COPY get_installed_version.py /tmp/get_installed_version.py
COPY --from=npmbuilder /src/scanomatic/ui_server_data/js/somlib /tmp/scanomatic/ui_server_data/js/somlib

RUN cd /tmp && python3.9 setup.py install --default
CMD scan-o-matic --no-browser
EXPOSE 5000
