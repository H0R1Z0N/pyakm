pyakm

To be python library for arch based kernel manager. (probably with gui)

See the examples under scripts/ directory. These scripts are packaged as executables as well.

pyakm-status
- Returns the current status of official kernels 

pyakm-install-latest [kernel]
- Installs latest version of given kernel

pyakm-remove-kernel [kernel]
- Removes the specified kernel

pyakm-downgrade-kernel [kernel]
- Downgrade specified kernel. Asks for possible options

pyakm-select-default -k [kernel]
- To switch default kernel. Simply adds first grub entry as pyakm default ([kernel])

To disable this feature (go back to antergos defaults)
- pyakm-select-default -d
