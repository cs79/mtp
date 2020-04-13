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
RUN cd /usr/lib \
    && wget 'https://dl.bintray.com/boostorg/release/1.72.0/source/boost_1_72_0.tar.bz2' \
    && mkdir boost && cd boost \
    && tar -jxvf /usr/lib/boost_1_72_0.tar.bz2 \
    && cd boost_1_72_0 \
    && ./bootstrap.sh \
    && ./b2 install \
    && export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib \
    && ldconfig \
    && rm -f /usr/lib/boost_1_72_0.tar.bz

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
RUN cd ~ \
    && mkdir bdb4 \
    && wget 'http://download.oracle.com/berkeley-db/db-4.8.30.NC.tar.gz' \
    && tar -xzvf db-4.8.30.NC.tar.gz \
    && sed -i 's/__atomic_compare_exchange/__atomic_compare_exchange_db/g' \
              db-4.8.30.NC/dbinc/atomic.h \
    && cd db-4.8.30.NC/build_unix/ \
    && ../dist/configure --enable-cxx --disable-shared --with-pic \
       --prefix=/root/bdb4/ \
    && make install

# install Python & libraries for Elements app development
RUN yum install -y python3 \
    && pip3 install virtualenv

# install Elements
RUN cd ~/elements \
    && ./autogen.sh \
    && ./configure LDFLAGS="-L/root/bdb4/lib/" \
                   CPPFLAGS="-I/root/bdb4/include/" \
    && make \
    && make install

# configure Elements test environment
RUN cd ~ \
    && mkdir elementsdir1 \
    && mkdir elementsdir2 \
    && cp ~/elements/contrib/assets_tutorial/elements1.conf \
          ~/elementsdir1/elements.conf \
    && cp ~/elements/contrib/assets_tutorial/elements2.conf \
          ~/elementsdir2/elements.conf \
    && cd ~/elementsdir1 \
    && sed -i 's/validatepegin=1/validatepegin=0/g' elements.conf \
    && echo -e '\ndatadir=/elementsdata\nwalletdir=/elementswallets' \
            >> elements.conf \
    && cd ~/elementsdir2 \
    && sed -i 's/validatepegin=1/validatepegin=0/g' elements.conf \
    && echo -e '\ndatadir=/elementsdata\nwalletdir=/elementswallets' \
            >> elements.conf

# set up aliases for Elements test example
RUN cd ~/elements/src \
    && shopt -s expand_aliases \
    && echo 'alias e1-dae="$HOME/elements/src/elementsd \
            -datadir=$HOME/elementsdir1"' >> ~/.bashrc \
    && echo 'alias e1-cli="$HOME/elements/src/elements-cli \
            -datadir=$HOME/elementsdir1"' >> ~/.bashrc \
    && echo 'alias e2-dae="$HOME/elements/src/elementsd \
            -datadir=$HOME/elementsdir2"' >> ~/.bashrc \
    && echo 'alias e2-cli="$HOME/elements/src/elements-cli \
            -datadir=$HOME/elementsdir2"' >> ~/.bashrc \
    && echo 'alias e1-qt="$HOME/elements/src/qt/elements-qt \
            -datadir=$HOME/elementsdir1"' >> ~/.bashrc \
    && echo 'alias e2-qt="$HOME/elements/src/qt/elements-qt \
            -datadir=$HOME/elementsdir2"' >> ~/.bashrc

# install tmux for development convenience
RUN cd ~ \
    && wget https://invisible-mirror.net/archives/ncurses/ncurses-6.2.tar.gz \
    && tar -xvzf ncurses-6.2.tar.gz \
    && cd ncurses-6.2 \
    && ./configure && make && make install \
    && cd ~ \
    && wget http://mirror.rit.edu/gnu/texinfo/texinfo-6.7.tar.gz \
    && tar -xvzf texinfo-6.7.tar.gz \
    && cd texinfo-6.7 \
    && ./configure && make && make install \
    && cd ~ \
    && wget http://mirror.rit.edu/gnu/help2man/help2man-1.43.3.tar.gz \
    && tar -xvzf help2man-1.43.3.tar.gz \
    && cd help2man-1.43.3 \
    && ./configure && make && make install \
    && cd ~ \
    && wget http://mirror.rit.edu/gnu/bison/bison-3.5.4.tar.gz \
    && tar -xvzf bison-3.5.4.tar.gz \
    && cd bison-3.5.4 \
    && ./configure && make && make install \
    && cd ~ \
    && git clone https://github.com/tmux/tmux.git \
    && cd tmux \
    && sh autogen.sh \
    && ./configure && make && make install

# install Python libraries for development convenience
RUN pip3 install pyyaml pandas ipython python-bitcoinrpc

# configure environment variable for Boost
ENV LD_LIBRARY_PATH=/usr/local/lib

# configure ports
EXPOSE 8332 18332 18443 18884

# configure volumes for wallet store and block store
VOLUME ["/elementsdata"]
VOLUME ["/elementswallets"]

# set entrypoint for Elements
CMD elementsd -validatepegin=0 -datadir=/elementsdata -walletdir=/elementswallets -rpcallowip=127.0.0.1 -rpcuser="user1" -rpcpassword="password1" -rpcport=18884 -rpcbind=127.0.0.1:18884 -chain=regtest
