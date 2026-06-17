FROM gcc:13

WORKDIR /sandbox

RUN useradd -m sandbox_user

USER sandbox_user

CMD ["bash"]