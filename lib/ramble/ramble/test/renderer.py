# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest
import ramble.renderer

def test_renderer_vector_expansion():
    renderer = ramble.renderer.Renderer()
    rg = ramble.renderer.RenderGroup("experiment", "create")
    rg.variables = {
        "var1": ["1", "2", "3", "4"],
        "var2": ["a", "b", "c", "d"]
    }
    # No matrix, just vectors. Should zip them.
    # Count should be max length = 4.
    # We must set ignore_used=False to force expansion of variables not used in templates (since we have no templates here)

    results = list(renderer.render_objects(rg, ignore_used=False))
    assert len(results) == 4

    # Check content
    assert results[0][0]["var1"] == "1"
    assert results[0][0]["var2"] == "a"
    assert results[3][0]["var1"] == "4"
    assert results[3][0]["var2"] == "d"

def test_renderer_matrix_expansion():
    renderer = ramble.renderer.Renderer()
    rg = ramble.renderer.RenderGroup("experiment", "create")
    rg.variables = {
        "var1": ["1", "2"],
        "var2": ["a", "b", "c"]
    }
    rg.matrices = [["var1", "var2"]]

    # Matrix of 2 * 3 = 6
    # Matrix variables are automatically considered "used"
    results = list(renderer.render_objects(rg))
    assert len(results) == 6

    # Check uniqueness
    experiments = set()
    for res, _ in results:
        experiments.add((res["var1"], res["var2"]))
    assert len(experiments) == 6
    assert ("1", "a") in experiments
    assert ("2", "c") in experiments

def test_renderer_multiple_matrices():
    renderer = ramble.renderer.Renderer()
    rg = ramble.renderer.RenderGroup("experiment", "create")
    rg.variables = {
        "var1": ["1", "2"],
        "var2": ["a", "b"],
        "var3": ["x", "y"],
        "var4": ["foo", "bar"]
    }
    # Two matrices, must have same size.
    # Matrix 1: var1 * var2 = 2 * 2 = 4 elements
    # Matrix 2: var3 * var4 = 2 * 2 = 4 elements
    rg.matrices = [["var1", "var2"], ["var3", "var4"]]

    results = list(renderer.render_objects(rg))
    assert len(results) == 4

    # It should zip the results of the two matrices.
    # Matrix 1 order: (1,a), (1,b), (2,a), (2,b)
    # Matrix 2 order: (x,foo), (x,bar), (y,foo), (y,bar)
    # Result 0: 1, a, x, foo

    assert results[0][0]["var1"] == "1"
    assert results[0][0]["var3"] == "x"
    assert results[3][0]["var1"] == "2"
    assert results[3][0]["var2"] == "b"
    assert results[3][0]["var3"] == "y"
    assert results[3][0]["var4"] == "bar"

def test_renderer_matrix_and_vector():
    renderer = ramble.renderer.Renderer()
    rg = ramble.renderer.RenderGroup("experiment", "create")
    rg.variables = {
        "var1": ["1", "2"], # Matrix var
        "var2": ["a", "b"], # Matrix var
        "vec1": ["v1", "v2", "v3"] # Vector var
    }
    rg.matrices = [["var1", "var2"]]

    # Matrix size: 2 * 2 = 4
    # Vector size: 3
    # Total: Cross Product of (Vector Indices) X (Matrix Objects)
    # Vector size 3. Matrix size 4. Total = 12.
    # Must use ignore_used=False for vec1 to be expanded.

    results = list(renderer.render_objects(rg, ignore_used=False))
    assert len(results) == 12

def test_renderer_zip_in_matrix():
    renderer = ramble.renderer.Renderer()
    rg = ramble.renderer.RenderGroup("experiment", "create")
    rg.variables = {
        "var1": ["1", "2", "3"],
        "var2": ["a", "b", "c"],
        "var3": ["x", "y"]
    }
    rg.zips = {
        "zip1": ["var1", "var2"]
    }
    # Zip length is 3.
    # Matrix: zip1 * var3 = 3 * 2 = 6.
    rg.matrices = [["zip1", "var3"]]

    results = list(renderer.render_objects(rg))
    assert len(results) == 6

    # Check values
    # var1 and var2 should move in lockstep
    for res, _ in results:
        idx = int(res["var1"]) - 1
        assert res["var2"] == rg.variables["var2"][idx]

def test_large_matrix_count():
    # Performance/Scale test
    renderer = ramble.renderer.Renderer()
    rg = ramble.renderer.RenderGroup("experiment", "create")
    size = 10
    rg.variables = {
        "d1": [str(i) for i in range(size)],
        "d2": [str(i) for i in range(size)],
        "d3": [str(i) for i in range(size)],
    }
    rg.matrices = [["d1", "d2", "d3"]]

    # 10 * 10 * 10 = 1000
    count = 0
    for _ in renderer.render_objects(rg):
        count += 1
    assert count == 1000
