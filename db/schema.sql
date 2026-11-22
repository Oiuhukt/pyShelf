CREATE TABLE "Book" (
	id INTEGER NOT NULL, 
	title VARCHAR NOT NULL, 
	author VARCHAR, 
	categories VARCHAR, 
	cover VARCHAR, 
	pages INTEGER, 
	progress FLOAT, 
	file_name VARCHAR NOT NULL, 
	description VARCHAR, 
	date DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	rights VARCHAR, 
	tags VARCHAR, 
	identifier VARCHAR, 
	publisher VARCHAR, 
	sample_text VARCHAR, 
	PRIMARY KEY (id)
);
CREATE TABLE "Collection" (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);
CREATE TABLE "User" (
	id INTEGER NOT NULL, 
	username VARCHAR NOT NULL, 
	password VARCHAR NOT NULL, 
	email VARCHAR, 
	date_joined DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	last_login DATETIME DEFAULT CURRENT_TIMESTAMP, 
	is_active BOOLEAN NOT NULL, 
	is_admin BOOLEAN NOT NULL, 
	is_superuser BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (email)
);
CREATE TABLE "BookCollection" (
	id INTEGER NOT NULL, 
	book_id INTEGER NOT NULL, 
	collection_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(book_id) REFERENCES "Book" (id), 
	FOREIGN KEY(collection_id) REFERENCES "Collection" (id)
);
CREATE UNIQUE INDEX "ix_Book_file_name" ON "Book" (file_name);
CREATE VIRTUAL TABLE Book_fts USING fts5(
    title, author, categories, tags, description, publisher, sample_text,
    content='Book',
    content_rowid='id',
    tokenize="unicode61 remove_diacritics 2"
);
/* Book_fts(title,author,categories,tags,description,publisher,sample_text) */
CREATE TABLE 'Book_fts_data'(id INTEGER PRIMARY KEY, block BLOB);
CREATE TABLE 'Book_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;
CREATE TABLE 'Book_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB);
CREATE TABLE 'Book_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID;
CREATE TRIGGER Book_ai AFTER INSERT ON Book BEGIN
  INSERT INTO Book_fts(rowid, title, author, categories, tags, description, publisher, sample_text)
  VALUES (new.id, new.title, new.author, new.categories, new.tags, new.description, new.publisher, new.sample_text);
END;
CREATE TRIGGER Book_ad AFTER DELETE ON Book BEGIN
  INSERT INTO Book_fts(Book_fts, rowid, title, author, categories, tags, description, publisher, sample_text)
  VALUES('delete', old.id, old.title, old.author, old.categories, old.tags, old.description, old.publisher, old.sample_text);
END;
CREATE TRIGGER Book_au AFTER UPDATE ON Book BEGIN
  INSERT INTO Book_fts(Book_fts, rowid, title, author, categories, tags, description, publisher, sample_text)
  VALUES('delete', old.id, old.title, old.author, old.categories, old.tags, old.description, old.publisher, old.sample_text);
  INSERT INTO Book_fts(rowid, title, author, categories, tags, description, publisher, sample_text)
  VALUES (new.id, new.title, new.author, new.categories, new.tags, new.description, new.publisher, new.sample_text);
END;
