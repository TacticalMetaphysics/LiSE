CREATE TABLE game
 (front_board TEXT DEFAULT 'Physical', age INTEGER DEFAULT 0,
 seed INTEGER DEFAULT 0);
CREATE TABLE strings (stringname TEXT NOT NULL, language TEXT NOT
 NULL DEFAULT 'English', string TEXT NOT NULL, PRIMARY KEY(stringname,
 language));
