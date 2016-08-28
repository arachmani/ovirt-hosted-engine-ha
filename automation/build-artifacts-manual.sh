#!/bin/bash -xe
[[ -d exported-artifacts ]] \
|| mkdir -p exported-artifacts

[[ -d tmp.repos ]] \
|| mkdir -p tmp.repos

rm -rf output

SUFFIX=".$(date -u +%Y%m%d%H%M%S).git$(git rev-parse --short HEAD)"

./autogen.sh --system
./configure

# Run rpmbuild, assuming the tarball is in the project's directory
rpmbuild \
    -D "_topmdir $PWD/tmp.repos" \
    -D "_srcrpmdir $PWD/output" \
    -D "release_suffix ${SUFFIX}" \
    -ts ovirt-hosted-engine-ha-*.tar.gz

yum-builddep $PWD/output/ovirt-hosted-engine-ha*.src.rpm

rpmbuild \
    -D "_topmdir $PWD/tmp.repos" \
    -D "_rpmdir $PWD/output" \
    -D "release_suffix ${SUFFIX}" \
    --rebuild $PWD/output/ovirt-hosted-engine-ha-*.src.rpm

mv *.tar.gz exported-artifacts
find \
    "$PWD/output" \
    -iname \*.rpm \
    -exec mv {} exported-artifacts/ \;
