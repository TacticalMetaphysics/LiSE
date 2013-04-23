def deep_lookup(dic, keylst):
    key = keylst.pop()
    ptr = dic
    while keylst != []:
        ptr = ptr[key]
        key = keylst.pop()
    return ptr[key]


class SaveableMetaclass(type):
    def __new__(metaclass, clas, parents, attrs):
        if 'coldecls' not in attrs or 'primarykeys' not in attrs:
            return type(clas, parents, attrs)
        coldecls = attrs['coldecls']
        keynames = [key for key in coldecls]
        primarykeys = attrs['primarykeys']
        tablenames = [key for key in coldecls]

        if 'foreignkeys' in attrs:
            foreignkeys = attrs['foreignkeys']
        else:
            foreignkeys = {}
        if 'checks' in attrs:
            checks = attrs['checks']
        else:
            checks = {}
        for d in foreignkeys, checks:
            for tablename in tablenames:
                if tablename not in d:
                    d[tablename] = {}
        schemata = []
        inserts = {}
        deletes = {}
        detects = {}
        missings = {}
        keylen = {}
        rowlen = {}
        keyqms = {}
        rowqms = {}
        keystrs = {}
        rowstrs = {}
        keynames = {}
        valnames = {}
        colnames = {}
        for item in primarykeys.iteritems():
            (tablename, pkey) = item
            keynames[tablename] = sorted(pkey)
            keylen[tablename] = len(pkey)
            keyqms[tablename] = ", ".join(["?"] * keylen[tablename])
            keystrs[tablename] = "(" + keyqms[tablename] + ")"
        for item in coldecls.iteritems():
            (tablename, coldict) = item
            valnames[tablename] = sorted(
                [key for key in coldict.keys()
                 if key not in keynames[tablename]])
            rowlen[tablename] = len(coldict)
            rowqms[tablename] = ", ".join(["?"] * rowlen[tablename])
            rowstrs[tablename] = "(" + rowqms[tablename] + ")"
        for tablename in coldecls.iterkeys():
            colnames[tablename] = keynames[tablename] + valnames[tablename]
        for tablename in tablenames:
            coldecl = coldecls[tablename]
            pkey = primarykeys[tablename]
            fkeys = foreignkeys[tablename]
            cks = ["CHECK(%s)" % ck for ck in checks[tablename]]
            pkeydecs = [keyname + " " + typ.upper()
                        for (keyname, typ) in coldecl.iteritems()
                        if keyname in pkey]
            valdecs = [valname + " " + typ.upper()
                       for (valname, typ) in coldecl.iteritems()
                       if valname not in pkey]
            coldecs = sorted(pkeydecs) + sorted(valdecs)
            coldecstr = ", ".join(coldecs)
            pkeycolstr = ", ".join(pkey)
            pkeys = [keyname for (keyname, typ) in coldecl.iteritems()
                     if keyname in pkey]
            pkeynamestr = ", ".join(sorted(pkeys))
            vals = [valname for (valname, typ) in coldecl.iteritems()
                    if valname not in pkey]
            colnamestr = ", ".join(sorted(pkeys) + sorted(vals))
            pkeystr = "PRIMARY KEY (%s)" % (pkeycolstr,)
            fkeystrs = ["FOREIGN KEY (%s) REFERENCES %s(%s)" %
                        (item[0], item[1][0], item[1][1])
                        for item in fkeys.iteritems()]
            fkeystr = ", ".join(fkeystrs)
            chkstr = ", ".join(cks)
            table_decl_data = [coldecstr, pkeystr]
            if len(fkeystrs) > 0:
                table_decl_data.append(fkeystr)
            if len(cks) > 0:
                table_decl_data.append(chkstr)
            table_decl = ", ".join(table_decl_data)
            create_stmt = "CREATE TABLE %s (%s);" % (tablename, table_decl)
            insert_stmt_start = "INSERT INTO %s VALUES " % (
                tablename,)
            inserts[tablename] = insert_stmt_start
            delete_stmt_start = "DELETE FROM %s WHERE (%s) IN " % (
                tablename, pkeycolstr)
            deletes[tablename] = delete_stmt_start
            detect_stmt_start = "SELECT %s FROM %s WHERE (%s) IN " % (
                colnamestr, tablename, pkeynamestr)
            detects[tablename] = detect_stmt_start
            missing_stmt_start = "SELECT %s FROM %s WHERE (%s) NOT IN " % (
                colnamestr, tablename, pkeynamestr)
            missings[tablename] = missing_stmt_start
            schemata.append(create_stmt)

        def dictify_rows(cols, rows):
            r = []
            for row in rows:
                assert len(cols) == len(row)
                d = {}
                i = 0
                while i < len(row):
                    col = cols[i]
                    val = row[i]
                    d[col] = val
                    i += 1
                r.append(d)
            return r

        def insert_rowdicts_table(db, rowdicts, tabname):
            rowstr = rowstrs[tabname]
            qrystr = inserts[tabname] + ", ".join([rowstr] * len(rowdicts))
            qrylst = []
            for rowdict in rowdicts:
                qrylst.extend([rowdict[col] for col in colnames[tabname]])
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)

        def delete_keydicts_table(db, keydicts, tabname):
            keystr = keystrs[tabname]
            qrystr = deletes[tabname] + ", ".join([keystr] * len(keydicts))
            qrylst = []
            for keydict in keydicts:
                qrylst.extend([keydict[col] for col in keynames[tabname]])
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)

        def detect_keydicts_table(db, keydicts, tabname):
            keystr = keystrs[tabname]
            qrystr = detects[tabname] + ", ".join([keystr] * len(keydicts))
            qrylst = []
            for keydict in keydicts:
                qrylst.extend([keydict[col] for col in keynames[tabname]])
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)
            return db.c.fetchall()

        def missing_keydicts_table(db, keydicts, tabname):
            keystr = keystrs[tabname]
            qrystr = missings[tabname] + ", ".join([keystr] * len(keydicts))
            qrylst = []
            for keydict in keydicts:
                qrylst.extend([keydict[col] for col in keynames[tabname]])
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)
            return db.c.fetchall()

        dbop = {'insert': insert_rowdicts_table,
                'delete': delete_keydicts_table,
                'detect': detect_keydicts_table,
                'missing': missing_keydicts_table}
        atrdic = {'coldecls': coldecls,
                  'colnames': colnames,
                  'primarykeys': primarykeys,
                  'foreignkeys': foreignkeys,
                  'checks': checks,
                  'schemata': schemata,
                  'keylen': keylen,
                  'rowlen': rowlen,
                  'keyqms': keyqms,
                  'rowqms': rowqms,
                  'dbop': dbop}
        atrdic.update(attrs)

        return type.__new__(metaclass, clas, parents, atrdic)
