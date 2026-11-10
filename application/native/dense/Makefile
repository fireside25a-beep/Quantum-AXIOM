CC ?= gcc
ASFLAGS = -Wall -Wextra -Werror -Wa,--fatal-warnings -fno-pie -no-pie -Wl,-z,noexecstack
.PHONY: all clean
all: bin/native_q_seed bin/native_q_compile bin/native_q_execute bin/native_q_inspect sdk/libnative_quantum_abi.so
bin sdk:
	mkdir -p $@
bin/native_q_seed bin/native_q_compile bin/native_q_execute bin/native_q_inspect: | bin
sdk/native_packet_abi.o sdk/libnative_quantum_abi.a sdk/libnative_quantum_abi.so: | sdk
sdk/%.o: source/%.S | sdk
	$(CC) -Wall -Wextra -Werror -Wa,--fatal-warnings -fPIC -c -o $@ $<
bin/native_q_seed: sdk/native_entropy_seed.o
	$(CC) -nostdlib -no-pie -Wl,-z,noexecstack -o $@ $<
bin/native_q_compile: sdk/native_q_compile.o sdk/libnative_quantum_abi.a
	$(CC) $(ASFLAGS) -o $@ $< sdk/libnative_quantum_abi.a
bin/native_q_execute: sdk/native_q_execute.o
	$(CC) $(ASFLAGS) -o $@ $<
sdk/native_packet_abi.o: source/native_packet_abi.S
	$(CC) -Wall -Wextra -Werror -Wa,--fatal-warnings -fPIC -c -o $@ $<
sdk/libnative_quantum_abi.a: sdk/native_packet_abi.o
	ar rcs $@ $<
sdk/libnative_quantum_abi.so: sdk/native_packet_abi.o
	$(CC) -shared -Wl,-z,noexecstack -o $@ $<
bin/native_q_inspect: sdk/native_packet_inspect.o sdk/libnative_quantum_abi.a
	$(CC) $(ASFLAGS) -o $@ $< sdk/libnative_quantum_abi.a
clean:
	rm -f bin/native_q_seed bin/native_q_compile bin/native_q_execute bin/native_q_inspect sdk/*.o sdk/*.a sdk/*.so
