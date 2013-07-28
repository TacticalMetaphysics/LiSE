INSERT INTO pawn_img (thing) VALUES ('me'), ('mom');
INSERT INTO pawn_interactive (thing) SELECT thing FROM pawn_img;
