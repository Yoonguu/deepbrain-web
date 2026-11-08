import assert from 'node:assert/strict';
import {intersectionAngle} from '../../frontend/workspace.js';
const a=[[0,0,0],[10,0,0]];
assert.equal(intersectionAngle(a,[[5,-5,0],[5,5,0]]).degrees,90);
assert.equal(intersectionAngle(a,[[5,-5,1],[5,5,1]]),null,'projected crossing is not a real crossing');
assert.equal(intersectionAngle(a,[[11,-5,0],[11,5,0]]),null,'line extensions must not count');
assert.equal(intersectionAngle(a,[[0,1,0],[10,1,0]]),null);
assert.equal(intersectionAngle([[0,0,0],[0,0,0]],a),null);
console.log('5 intersection geometry checks passed');
