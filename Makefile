packer = tar
pack = $(packer) -caf
unpack = $(packer) --keep-newer-files -xaf
arcx = .tar.xz
#
imagedir = .
# ./images
backupdir = ~/shareddocs/pgm/python/
distribdir = ~/downloads
#
basename = dmxgrad
srcversion = dmxgrad
version = r$(shell python3 -c 'from $(srcversion) import REVISION; print(REVISION)')
branch = $(shell git symbolic-ref --short HEAD)
title = $(basename)
title_version = "$(title) r$(version)"
#
todo = TODO
readme = README.md
docs = $(todo) Changelog COPYING $(readme)
zipname = $(basename).zip
arcname = $(basename)$(arcx)
srcarcname = $(basename)-$(branch)-src$(arcx)
pysrcs = *.py
uisrcs =
# *.ui
#grsrcs = $(imagedir)/*.svg
grsrcs = *.png *.svg
srcs = $(pysrcs) $(uisrcs) $(grsrcs)

app:
	zip $(zipname) $(srcs)
	python3 -m zipapp $(zipname) -o $(basename) -p "/usr/bin/env python3" -c
	rm $(zipname)

archive:
	make todo
	$(pack) $(srcarcname) $(srcs) Makefile *.geany $(docs)

distrib:
	make app
	make desktop
	make winiconfn
	make todo
	$(eval distname = $(basename)-$(version)$(arcx))
	$(pack) $(distname) $(basename) $(docs) $(desktopfn) $(winiconfn)
	mv $(distname) $(distribdir)

backup:
	make archive
	mv $(srcarcname) $(backupdir)

update:
	$(unpack) $(backupdir)$(srcarcname)

commit:
	make todo
	git commit -a -uno -m "$(version)"
	@echo "не забудь сказать git push"

show-branch:
	@echo "$(branch)-$(version)"

docview:
	$(eval docname = README.htm)
	grip $(readme) --export $(docname) --no-inline
	x-www-browser $(docname)
	#rm $(docname)

todo:
	pytodo.py $(pysrcs) >$(todo)

help:
	python3 -c "import $(srcversion); help($(srcversion))"
