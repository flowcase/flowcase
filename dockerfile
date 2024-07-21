FROM nginx:1.27

VOLUME [ "/flowcase/data" ]

WORKDIR /flowcase
ADD . /flowcase

RUN apt-get update

# Install python
RUN apt-get install -y python3 python3-pip

# Install python dependencies
RUN pip install --break-system-packages --trusted-host pypi.python.org -r requirements.txt

# copy all nginx configuration files
RUN rm /etc/nginx/conf.d/default.conf
COPY ./nginx /etc/nginx/conf.d

RUN chmod +x /flowcase/start.sh
ENTRYPOINT [ "/flowcase/start.sh" ]