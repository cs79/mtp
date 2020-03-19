FROM ubuntu:bionic

# get Elements source from git
RUN cd ~ && apt-get update && apt install -y git && \
    git clone https://github.com/ElementsProject/elements.git

# install Elements dependencies
RUN apt-get install -y build-essential libtool autotools-dev autoconf \
                    pkg-config libssl-dev \
    && apt-get install -y libboost-all-dev \
    && apt-get install -y libqt5gui5 libqt5core5a libqt5dbus5 qttools5-dev \
                       qttools5-dev-tools libprotobuf-dev protobuf-compiler \
                       imagemagick librsvg2-bin \
    && apt-get install -y libqrencode-dev autoconf openssl libssl-dev libevent-dev \
    && apt-get install -y libminiupnpc-dev && apt install -y jq \
    && apt-get install -y wget \
    && apt-get install -y bsdmainutils

# build and install Berkeley database
RUN mkdir bdb4 \
    && wget 'http://download.oracle.com/berkeley-db/db-4.8.30.NC.tar.gz' \
    && tar -xzvf db-4.8.30.NC.tar.gz \
    && sed -i 's/__atomic_compare_exchange/__atomic_compare_exchange_db/g' \
              db-4.8.30.NC/dbinc/atomic.h \
    && cd db-4.8.30.NC/build_unix/ \
    && ../dist/configure --enable-cxx --disable-shared --with-pic \
                         --prefix=/root/bdb4/ \
    && make install

# build and install Elements
RUN cd ~/elements \
    && ./autogen.sh \
    && ./configure LDFLAGS="-L/root/bdb4/lib/" \
                   CPPFLAGS="-I/root/bdb4/include/" \
    && make \
    && make install

# install Python & libraries for Elements app development
RUN apt-get install -y python3-pip \
    && pip3 install virtualenv

# cleanup
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
