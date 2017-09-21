import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import pyakm.kernel_module as kernel_module
import re

class Handler:

    def on_tree_selection_changed(selection):
        model, treeiter = selection.get_selected()
        if treeiter != None:
            print("You selected", model[treeiter][0],
                  model[treeiter][1], model[treeiter][2])

def _argsort(arr):
    return sorted(range(len(arr)), key=arr.__getitem__)
    

def grab_kernel_packages_by_name(kernel_name):
    
    kernel_id = kernel_module.kernel_dicts[kernel_name]
    kernel_list = kernel_module.grab_kernel_official()
    packages = kernel_module.grab_package_list(kernel_list[kernel_id])
    return packages

def parse_package_versions(kernel_name, packages):

    pass
    

def sort_and_filter_packages(kernel_name, packages):

    pkg_vers = []
    bads = []

    for i,pkg in enumerate(packages):
        res = re.match(kernel_name+"-(\w+).(\w+).(\w+)-(\w+)-x", pkg)
        if res != None:
            pkg_vers.append("%02d%02d%02d%02d" % \
                            (int(res.group(1)),int(res.group(2)),
                             int(res.group(3)),int(res.group(4))))
        else:
            bads.append(i)

    for bad in bads[::-1]:
        packages.pop(bad)
    
    sorted_ndx = _argsort(pkg_vers)
    pkg_vers.sort()

    tmp_packages = [None]*len(sorted_ndx)
    for i in range(len(sorted_ndx)):
        tmp_packages[i] = packages[sorted_ndx[i]]

    pkg_vers = pkg_vers[::-1]
    packages = tmp_packages[::-1]
            
    new_packages = []
    last_vers = ""
                    
    for i in range(len(packages)):
        vers = str(pkg_vers[i])[:4]
        if last_vers != vers:
            new_packages.append(packages[i])
            last_vers = vers

    return new_packages
            
    
def create_treeview1(builder):

    treeview = builder.get_object("treeview")
    renderer = Gtk.CellRendererText()
    column = Gtk.TreeViewColumn("Kernel", renderer, text=0)
    treeview.append_column(column)
    renderer = Gtk.CellRendererText()
    column = Gtk.TreeViewColumn("Version", renderer, text=1)
    treeview.append_column(column)
    renderer = Gtk.CellRendererText()
    column = Gtk.TreeViewColumn("Revision", renderer, text=2)
    treeview.append_column(column)

    return treeview

def populate_list_store_from_packages(packages, kernel_name):

    liststore = Gtk.ListStore(str,str,str)

    for i,pkg in enumerate(packages):
        res = re.match(kernel_name+"-(\w+.\w+).(\w+-\w+)-x", pkg)
        print (kernel_name, str(res.group(1)), str(res.group(2)))
        liststore.append(list((kernel_name, str(res.group(1)), \
                               str(res.group(2)))))

    return liststore
            
