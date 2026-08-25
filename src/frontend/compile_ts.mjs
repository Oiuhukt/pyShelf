import fs from 'fs';
import { transform } from 'sucrase';

try {
    const source = fs.readFileSync('static/script/pyshelf.ts', 'utf8');

    const result = transform(source, {
        transforms: ['typescript']
    });

    fs.writeFileSync('static/script/pyshelf.js', result.code);
    console.log("Transpilation successful!");
} catch (err) {
    console.error("Error during transpilation:", err);
    process.exit(1);
}
