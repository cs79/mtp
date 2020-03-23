FROM registry.access.redhat.com/ubi8/ubi

# install epel
RUN dnf install -y \
    https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm

# get Elements source from git
RUN cd ~ && dnf install -y git \
    && git clone https://github.com/ElementsProject/elements.git

# install build dependencies
RUN yum install -y wget gcc gcc-c++ make autoconf automake libtool bzip2 \
                openssl-devel

# install Boost
RUN cd ~ \
    && wget 'https://dl.bintray.com/boostorg/release/1.72.0/source/boost_1_72_0.tar.bz2' \
    && mkdir boost && cd boost \
    && tar -jxvf /root/boost_1_72_0.tar.bz2 \
    && cd boost_1_72_0 \
    && ./bootstrap.sh \
    && ./b2 install

# install libevent
RUN yum remove libevent \
    && cd ~ \
    && wget https://github.com/libevent/libevent/releases/download/release-2.1.11-stable/libevent-2.1.11-stable.tar.gz \
    && tar xvf libevent-2.1.11-stable.tar.gz \
    && cd libevent-2.1.11-stable \
    && ./configure --prefix=/usr \
    && make \
    && make install

# install Berkeley DB
RUN mkdir bdb4 \
    && wget 'http://download.oracle.com/berkeley-db/db-4.8.30.NC.tar.gz' \
    && tar -xzvf db-4.8.30.NC.tar.gz \
    && sed -i 's/__atomic_compare_exchange/__atomic_compare_exchange_db/g' \
              db-4.8.30.NC/dbinc/atomic.h \
    && cd db-4.8.30.NC/build_unix/ \
    && ../dist/configure --enable-cxx --disable-shared --with-pic \
       --prefix=/root/bdb4/ \
    && make install

# install Elements
RUN cd ~/elements \
    && ./autogen.sh \
    && ./configure LDFLAGS="-L/root/bdb4/lib/" \
                   CPPFLAGS="-I/root/bdb4/include/" \
    && make \
    && make install

# install Python & libraries for Elements app development
RUN yum install -y python3 \
    && pip3 install virtualenv
