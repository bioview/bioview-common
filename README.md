# BioView Common

A collection of common configuration and protocol specification for BioView clients and servers

```Configuration``` objects act as context managers (*models*) for their respective UI components (*views*). They are initialized by user-passed JSONs and can be adjusted continuously throughout the experiment. The sub-types expose signals which can be binded to for on-the-fly parameter updates. Further, their updated states can be stored to update the pre-existing configuration files.
