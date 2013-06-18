CREATE TRIGGER name_place BEFORE INSERT ON place
BEGIN
INSERT INTO item (dimension, name) VALUES (NEW.dimension, NEW.name);
END;
CREATE TRIGGER name_portal BEFORE INSERT ON portal 
BEGIN
INSERT INTO item (dimension, name)
VALUES (NEW.dimension, 'Portal('||NEW.from_place||'->'||NEW.to_place||')');
END;
CREATE TRIGGER name_thing BEFORE INSERT ON thing
BEGIN
INSERT INTO item (dimension, name) VALUES (NEW.dimension, NEW.name);
END;
CREATE TRIGGER move_portal BEFORE UPDATE OF
from_place, to_place ON portal
BEGIN
UPDATE item SET name='Portal('||NEW.from_place||'->'||NEW.to_place||')'
WHERE dimension=old.dimension AND name='Portal('||OLD.from_place||'->'||OLD.to_place||')';
END;
CREATE TRIGGER del_place AFTER DELETE ON place
BEGIN
DELETE FROM item WHERE dimension=OLD.dimension AND name=OLD.name;
END;
CREATE TRIGGER del_port AFTER DELETE ON portal
BEGIN
DELETE FROM item WHERE dimension=OLD.dimension AND
name='Portal('||OLD.from_place||'->'||OLD.to_place||')';
END;
CREATE TRIGGER del_thing AFTER DELETE ON thing
BEGIN
DELETE FROM item WHERE dimension=OLD.dimension AND name=OLD.name;
END;
CREATE TRIGGER easy_effect_add INSTEAD OF INSERT ON easy_effect
BEGIN
INSERT INTO effect (name, func, arg) VALUES
(NEW.func||'('||NEW.arg||')', NEW.func, NEW.arg);
END;
